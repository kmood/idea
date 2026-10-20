"""Durable local run state. Public exports intentionally never read these tables."""
import hashlib
import json
import os
import stat
import time
from contextlib import closing
from .contracts import Fault, boundary, encoded, fields, now, require, stamp, string_list, text
from .exchange import digest
from .storage import Database
from .artifacts import hash_value

TABLES = ('research_runs', 'research_intents')
MAX_CACHE_BYTES = 16 * 1024 * 1024
SCHEMA = (
    'CREATE TABLE IF NOT EXISTS research_runs(run_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, payload TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS research_intents(run_id TEXT NOT NULL REFERENCES research_runs(run_id), intent_id TEXT NOT NULL, request_hash TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(run_id,intent_id))',
)


def cache_available(cache_dir, pointer):
    """Accept only an unexpired, bounded regular file matching its content address."""
    if not isinstance(pointer, dict):
        return False
    cache_key = pointer.get('cacheKey')
    expires_at = pointer.get('expiresAt')
    if not hash_value(cache_key) or type(expires_at) not in (int, float) or expires_at <= time.time():
        return False
    descriptor = None
    try:
        descriptor = os.open(cache_dir / (cache_key + '.json'), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return False
            payload = stream.read(MAX_CACHE_BYTES + 1)
        if len(payload) > MAX_CACHE_BYTES or hashlib.sha256(payload).hexdigest() != cache_key:
            return False
        json.loads(payload)
        return True
    except (OSError, ValueError, UnicodeError):
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)


def validate_request(request):
    keys = {'sourceIds', 'queries', 'limits', 'deadline'}
    fields(request, keys, keys)
    require(string_list(request['sourceIds']) and string_list(request['queries']))
    require(stamp(request['deadline']))
    keys = {'searches', 'candidates', 'auxiliary', 'total'}
    fields(request['limits'], keys, keys)
    require(all(type(v) is int and v >= 0 for v in request['limits'].values()))


def validate_intent(intent):
    keys = {'recordId', 'operationId', 'requestHash', 'expectedRevision'}
    fields(intent, keys, keys)
    require(text(intent['recordId']) and text(intent['operationId']) and hash_value(intent['requestHash']))
    require(intent['expectedRevision'] is None or (type(intent['expectedRevision']) is int and intent['expectedRevision'] > 0))


def get_run(conn, run_id):
    require(text(run_id))
    row = conn.execute('SELECT payload FROM research_runs WHERE run_id=?', (run_id,)).fetchone()
    if row is None:
        raise Fault('NOT_FOUND', 'Research run not found')
    return json.loads(row[0])


class ResearchRuntimeStore:
    def __init__(self, path, clock=None):
        self.db = Database(path)
        from .execution import ExecutionStore
        self.execution = ExecutionStore(self.db, clock)
        with closing(self.db.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                for statement in SCHEMA:
                    conn.execute(statement)
                conn.execute('CREATE TABLE IF NOT EXISTS research_execution(run_id TEXT PRIMARY KEY REFERENCES research_runs(run_id), payload TEXT NOT NULL)')
                conn.execute('CREATE TABLE IF NOT EXISTS research_publications(manifest_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES research_runs(run_id),draft_hash TEXT NOT NULL,payload TEXT NOT NULL)')
                conn.execute('COMMIT')
            finally:
                if conn.in_transaction:
                    conn.execute('ROLLBACK')

    @boundary
    def begin(self, run_id, request):
        require(text(run_id)); validate_request(request)
        def action(conn):
            run = dict(runId=run_id, request=request, requestHash=digest(request), createdAt=now(), status='pending')
            conn.execute('INSERT INTO research_runs VALUES (?,?,?)', (run_id, run['requestHash'], encoded(run)))
            return run
        return self.db.run('runtime-run', run_id, request, action)

    @boundary
    def save_intent(self, run_id, intent_id, intent, *, token=None):
        require(text(run_id) and text(intent_id)); validate_intent(intent)
        def action(conn):
            get_run(conn, run_id)
            result = dict(runId=run_id, intentId=intent_id, intent=intent, status='pending', result=None)
            conn.execute('INSERT INTO research_intents VALUES (?,?,?,?)', (run_id,intent_id,digest(intent),encoded(result)))
            return result
        return self.db.run('runtime-intent:' + run_id, intent_id, intent, action,
                           guard=lambda conn:self.execution.guard(conn, run_id, token))

    @boundary
    def inspect_run(self, run_id, cursor='', limit=20):
        require(isinstance(cursor,str) and type(limit) is int and 1 <= limit <= 100)
        with closing(self.db.connect()) as conn:
            conn.execute('BEGIN')
            try:
                run = get_run(conn, run_id)
                rows = conn.execute('SELECT intent_id,payload FROM research_intents WHERE run_id=? AND intent_id>? ORDER BY intent_id LIMIT ?', (run_id,cursor,limit+1)).fetchall()
                return dict(run=run, intents=[json.loads(row['payload']) for row in rows[:limit]],
                            nextCursor=rows[limit-1]['intent_id'] if len(rows)>limit else None)
            finally:
                conn.execute('ROLLBACK')

    @boundary
    def save_publication_plan(self, run_id, manifest_id, draft_hash, plan, *, token=None):
        from .artifacts import hash_value
        from .publishing import validate_plan
        require(text(run_id) and text(manifest_id) and hash_value(draft_hash))
        validate_plan(plan,run_id)
        require(plan['manifestId'] == manifest_id and plan['draftHash'] == draft_hash)
        require(len(encoded(plan).encode()) <= 1024*1024, 'Publication plan is too large')
        def action(conn):
            get_run(conn,run_id)
            conn.execute('INSERT INTO research_publications VALUES (?,?,?,?)',
                         (manifest_id,run_id,draft_hash,encoded(plan)))
            return plan
        return self.db.run('runtime-publication:'+run_id,manifest_id,plan,action,
                           guard=lambda conn:self.execution.guard(conn,run_id,token))

    @boundary
    def publication_plan(self, run_id, manifest_id, *, token=None):
        require(text(run_id) and text(manifest_id))
        def action(conn):
            from .publishing import validate_plan
            self.execution.guard(conn,run_id,token)
            row=conn.execute('SELECT draft_hash,payload FROM research_publications WHERE run_id=? AND manifest_id=?',
                             (run_id,manifest_id)).fetchone()
            if row is None:raise Fault('NOT_FOUND','Publication plan is not available locally')
            plan=json.loads(row['payload'])
            validate_plan(plan,run_id)
            require(plan['manifestId']==manifest_id and plan['draftHash']==row['draft_hash'])
            return plan
        return self.execution.transaction(action)

    @boundary
    def recovery_inventory(self):
        """Describe recoverable state without inventing private or unpublished data."""
        with closing(self.db.connect()) as conn:
            tables={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            artifacts=[json.loads(row[0]) for row in conn.execute("""SELECT payload FROM research_records
                WHERE kind='ResearchArtifact' AND json_extract(payload,'$.artifactType') IN
                ('ReadReceipt','PublicationManifest','SourceCheckpoint')
                AND json_extract(payload,'$.archived')=0 ORDER BY id""")]
            plan_ids=set()
            if 'research_publications' in tables:
                plan_ids={row[0] for row in conn.execute('SELECT manifest_id FROM research_publications')}
            pointers={}
            if 'research_readings' in tables:
                pointers={row['receipt_id']:json.loads(row['payload'])
                          for row in conn.execute('SELECT receipt_id,payload FROM research_readings')}
            manifests=[];checkpoints=[];receipts=[]
            cache_dir=self.db.path.parent/'research-cache'
            for record in artifacts:
                kind=record['artifactType'];data=record['data']
                if kind=='PublicationManifest':
                    pending=[step['targetId'] for step in data['steps'] if step['result'] is None]
                    local=record['id'] in plan_ids
                    action='complete' if not pending else ('resume_local_plan' if local else 'reread_and_reanalyze')
                    manifests.append(dict(recordId=record['id'],revision=record['revision'],runId=data['runId'],
                        candidateId=data['candidateId'],sourceId=data['sourceId'],pendingTargets=pending,
                        completedTargets=[step['targetId'] for step in data['steps'] if step['result'] is not None],
                        localPlan=local,nextAction=action))
                elif kind=='SourceCheckpoint':
                    checkpoints.append(dict(recordId=record['id'],revision=record['revision'],**data))
                else:
                    available=cache_available(cache_dir,pointers.get(record['id']))
                    receipts.append(dict(recordId=record['id'],revision=record['revision'],runId=data['runId'],
                        sourceId=data['sourceId'],originalUrl=data['originalUrl'],finalUrl=data['finalUrl'],
                        cacheStatus='available' if available else 'missing',
                        nextAction=None if available else 'reread'))
            run_count=conn.execute('SELECT count(*) FROM research_runs').fetchone()[0]
            pending=conn.execute("SELECT count(*) FROM research_intents WHERE json_extract(payload,'$.status')='pending'").fetchone()[0]
            private=conn.execute('SELECT count(*) FROM personal_states').fetchone()[0]
            return dict(mode='local-backup' if run_count else 'public-only',manifests=manifests,
                        checkpoints=checkpoints,receipts=receipts,localOnly=dict(runCount=run_count,
                        publicationPlanCount=len(plan_ids),pendingIntentCount=pending,privateStateCount=private))


def validate_runtime(conn):
    present = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    found = set(TABLES) & present
    if not found:
        return ()
    require(found == set(TABLES), 'Incomplete runtime schema')
    for row in conn.execute('SELECT * FROM research_runs'):
        run = json.loads(row['payload'])
        keys = {'runId','request','requestHash','createdAt','status'}
        fields(run,keys,keys); validate_request(run['request'])
        require(text(run['runId']) and run['runId'] == row['run_id'])
        require(stamp(run['createdAt']) and run['status'] == 'pending')
        require(run['requestHash'] == row['request_hash'] == digest(run['request']), 'Runtime request digest mismatch')
        validate_replay(conn, 'runtime-run', row['run_id'], row['request_hash'], run)
    for row in conn.execute('SELECT * FROM research_intents'):
        item = json.loads(row['payload'])
        keys = {'runId','intentId','intent','status','result'}
        fields(item,keys,keys); validate_intent(item['intent'])
        require(item['runId'] == row['run_id'] and text(item['intentId']) and item['intentId'] == row['intent_id'])
        get_run(conn,item['runId'])
        require(item['status'] in ('pending','completed'))
        if item['status'] == 'pending':
            require(item['result'] is None)
        else:
            from .artifacts import ref
            ref(item['result'])
            version = conn.execute('SELECT payload FROM record_versions WHERE record_id=? AND revision=?',
                                   (item['result']['recordId'],item['result']['revision'])).fetchone()
            require(version is not None, 'Completed publishing receipt lost its record version')
            operation = conn.execute('SELECT request_hash,result FROM operations WHERE scope=? AND key=?',
                                     ('research',item['intent']['operationId'])).fetchone()
            require(operation is not None and operation['request_hash'] == item['intent']['requestHash'],
                    'Completed publishing receipt lost its business operation')
            published = json.loads(operation['result'])
            require(published['id'] == item['result']['recordId'] and
                    published['revision'] == item['result']['revision'] and
                    published == json.loads(version['payload']),
                    'Completed publishing receipt differs from its business result')
        require(row['request_hash'] == digest(item['intent']))
        replay = item | {'status':'pending','result':None}
        validate_replay(conn, 'runtime-intent:' + item['runId'], item['intentId'], row['request_hash'], replay)
    if 'research_execution' in present:
        from .execution import validate_execution
        validate_execution(conn)
        extra = ('research_execution',)
    else:
        extra = ()
    if 'research_network' in present:
        from .network_policy import validate_network
        validate_network(conn)
        extra += ('research_network',)
    if 'research_readings' in present:
        from .readings import validate_readings
        validate_readings(conn)
        extra += ('research_readings',)
    if {'research_searches','research_candidates'} & present:
        from .discovery import TABLES as discovery_tables,validate_discovery
        require(set(discovery_tables)<=present,'Incomplete discovery schema')
        validate_discovery(conn)
        extra += discovery_tables
    if 'research_publications' in present:
        from .publishing import validate_plan
        for row in conn.execute('SELECT * FROM research_publications'):
            get_run(conn,row['run_id'])
            plan=json.loads(row['payload'])
            validate_plan(plan,row['run_id'])
            require(plan['manifestId']==row['manifest_id'] and plan['draftHash']==row['draft_hash'])
            validate_replay(conn,'runtime-publication:'+row['run_id'],row['manifest_id'],digest(plan),plan)
        extra += ('research_publications',)
    if 'research_progress' in present:
        from .progress import validate_progress
        validate_progress(conn);extra += ('research_progress',)
    return TABLES + extra


def validate_replay(conn, scope, key, request_hash, result):
    row = conn.execute('SELECT request_hash,result FROM operations WHERE scope=? AND key=?', (scope,key)).fetchone()
    require(row is not None and row['request_hash'] == request_hash and json.loads(row['result']) == result,
            'Runtime replay differs from saved state')
