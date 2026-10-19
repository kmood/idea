"""Durable local run state. Public exports intentionally never read these tables."""
import json
from contextlib import closing
from .contracts import Fault, boundary, encoded, fields, now, require, stamp, string_list, text
from .exchange import digest
from .storage import Database
from .artifacts import hash_value

TABLES = ('research_runs', 'research_intents')
SCHEMA = (
    'CREATE TABLE IF NOT EXISTS research_runs(run_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, payload TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS research_intents(run_id TEXT NOT NULL REFERENCES research_runs(run_id), intent_id TEXT NOT NULL, request_hash TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(run_id,intent_id))',
)


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
        require(item['status'] == 'pending' and item['result'] is None)
        require(row['request_hash'] == digest(item['intent']))
        validate_replay(conn, 'runtime-intent:' + item['runId'], item['intentId'], row['request_hash'], item)
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
    return TABLES + extra


def validate_replay(conn, scope, key, request_hash, result):
    row = conn.execute('SELECT request_hash,result FROM operations WHERE scope=? AND key=?', (scope,key)).fetchone()
    require(row is not None and row['request_hash'] == request_hash and json.loads(row['result']) == result,
            'Runtime replay differs from saved state')
