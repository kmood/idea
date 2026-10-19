"""Database-wide lease and durable call grants, checked in short transactions."""
import json
import math
import time
from contextlib import closing
from datetime import datetime
from .contracts import Fault, boundary, encoded, fields, require, stamp, text
from .artifacts import hash_value

TOKEN_KEYS = {'dbInstanceId','ownerId','runId','fence','leaseUntil'}
KINDS = ('search','discussion','auxiliary','request')


def metadata(conn, key):
    row = conn.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
    return json.loads(row[0]) if row else None


def put_metadata(conn,key,value):
    conn.execute('INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,encoded(value)))


def usage(calls):
    return dict(total=len(calls),searches=sum(c['kind']=='search' for c in calls),
                candidates=len({c['identity'] for c in calls if c['kind']=='discussion'}),
                auxiliary=len({c['identity'] for c in calls if c['kind']=='auxiliary'}))


class ExecutionStore:
    def __init__(self, db, clock=None):
        self.db, self.clock = db, clock or time.time

    def transaction(self, action):
        with closing(self.db.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                result = action(conn)
                conn.execute('COMMIT')
                return result
            finally:
                if conn.in_transaction:
                    conn.execute('ROLLBACK')

    def guard(self,conn,run_id,token):
        fields(token,TOKEN_KEYS,TOKEN_KEYS)
        require(all(text(token[k]) for k in ('dbInstanceId','runId','ownerId')) and type(token['fence']) is int)
        require(type(token['leaseUntil']) in (float,int) and math.isfinite(token['leaseUntil']))
        lease = metadata(conn,'researchLease')
        current = self.clock()
        require(math.isfinite(current) and current >= 0)
        instance = conn.execute("SELECT value FROM metadata WHERE key='dbInstanceId'").fetchone()[0]
        if (not lease or token['dbInstanceId'] != instance or token['runId'] != run_id or
                any(token[key] != lease[key] for key in ('dbInstanceId','runId','ownerId','fence')) or current >= lease['leaseUntil']):
            raise Fault('LEASE_EXPIRED','Resume to acquire execution ownership')
        return current

    @boundary
    def acquire(self,run_id,owner_id):
        from .runtime import get_run
        require(text(owner_id))
        def action(conn):
            get_run(conn,run_id)
            previous = metadata(conn,'researchLease')
            current = self.clock()
            require(math.isfinite(current) and current >= 0)
            same = previous and previous['runId'] == run_id and previous['ownerId'] == owner_id
            active = previous and current < previous['leaseUntil']
            if active and not same:
                raise Fault('BUSY','Another research executor owns this database')
            instance = conn.execute("SELECT value FROM metadata WHERE key='dbInstanceId'").fetchone()[0]
            fence = previous['fence'] if active and same else (previous['fence']+1 if previous else 1)
            token = dict(dbInstanceId=instance,runId=run_id,ownerId=owner_id,fence=fence,leaseUntil=current+90)
            put_metadata(conn,'researchLease',token)
            return token
        return self.transaction(action)

    def ledger(self,conn,run_id):
        from .runtime import get_run
        get_run(conn,run_id)
        row = conn.execute('SELECT payload FROM research_execution WHERE run_id=?',(run_id,)).fetchone()
        return json.loads(row[0]) if row else dict(calls={},grants={},cancelled=False)

    def save(self,conn,run_id,ledger):
        conn.execute('INSERT INTO research_execution VALUES (?,?) ON CONFLICT(run_id) DO UPDATE SET payload=excluded.payload',(run_id,encoded(ledger)))

    def limits(self,conn,run_id,ledger):
        from .runtime import get_run
        request = get_run(conn,run_id)['request']
        limits = dict(request['limits'])
        deadline = datetime.fromisoformat(request['deadline']).timestamp()
        for grant in ledger['grants'].values():
            for key in limits:
                limits[key] += grant['increments'][key]
            deadline = max(deadline,datetime.fromisoformat(grant['deadline']).timestamp())
        return limits,deadline

    @boundary
    def reserve(self,run_id,token,call_id,kind,identity=None):
        require(text(call_id) and kind in KINDS)
        require(text(identity) if kind in ('discussion','auxiliary') else identity is None)
        def action(conn):
            current = self.guard(conn,run_id,token)
            ledger = self.ledger(conn,run_id)
            limits,deadline = self.limits(conn,run_id,ledger)
            if ledger['cancelled']:
                raise Fault('CANCELLED','Research run was cancelled')
            if current >= deadline:
                raise Fault('DEADLINE_EXCEEDED','Explicit extension required')
            prior = ledger['calls'].get(call_id)
            if prior:
                if prior['kind'] != kind or prior['identity'] != identity:
                    raise Fault('IDEMPOTENCY_CONFLICT','Call ID has a different request')
                if current >= prior['expiresAt']:
                    raise Fault('CALL_EXPIRED','A new attempt needs a new call ID and budget')
                return prior
            calls = list(ledger['calls'].values()) + [dict(kind=kind,identity=identity)]
            used = usage(calls)
            if any(used[key]>limits[key] for key in limits):
                raise Fault('BUDGET_EXHAUSTED','No remaining call budget')
            grant = dict(callId=call_id,kind=kind,identity=identity,reservedAt=current,
                         expiresAt=min(current+30,deadline),status='reserved',resultHash=None)
            ledger['calls'][call_id] = grant
            self.save(conn,run_id,ledger)
            return grant
        return self.transaction(action)

    @boundary
    def finish(self,run_id,token,call_id,result_hash):
        require(text(call_id) and hash_value(result_hash))
        def action(conn):
            current = self.guard(conn,run_id,token)
            ledger = self.ledger(conn,run_id)
            call = ledger['calls'].get(call_id)
            require(call is not None,'Call was never reserved')
            if call['status'] == 'completed':
                if call['resultHash'] != result_hash:
                    raise Fault('IDEMPOTENCY_CONFLICT','Call result changed')
                return call
            if ledger['cancelled'] or current >= call['expiresAt']:
                raise Fault('CALL_EXPIRED','Late results are not accepted')
            call.update(status='completed',resultHash=result_hash)
            self.save(conn,run_id,ledger)
            return call
        return self.transaction(action)

    @boundary
    def extend(self,run_id,token,authorization_id,increments,deadline):
        require(text(authorization_id) and stamp(deadline))
        keys = {'searches','candidates','auxiliary','total'}
        fields(increments,keys,keys)
        require(all(type(value) is int and value>=0 for value in increments.values()))
        grant = dict(increments=increments,deadline=deadline)
        def action(conn):
            self.guard(conn,run_id,token)
            ledger = self.ledger(conn,run_id)
            previous = ledger['grants'].get(authorization_id)
            if previous is not None and previous != grant:
                raise Fault('IDEMPOTENCY_CONFLICT','Authorization already used for another extension')
            ledger['grants'][authorization_id] = grant
            self.save(conn,run_id,ledger)
            return grant
        return self.transaction(action)

    @boundary
    def cancel(self,run_id,token):
        def action(conn):
            self.guard(conn,run_id,token)
            ledger = self.ledger(conn,run_id)
            ledger['cancelled'] = True
            self.save(conn,run_id,ledger)
            return dict(cancelled=True)
        return self.transaction(action)


    @boundary
    def inspect(self,run_id,cursor='',limit=20):
        require(isinstance(cursor,str) and type(limit) is int and 1 <= limit <= 100)
        with closing(self.db.connect()) as conn:
            conn.execute('BEGIN')
            try:
                ledger = self.ledger(conn,run_id)
                limits,deadline = self.limits(conn,run_id,ledger)
                used = usage(list(ledger['calls'].values()))
                keys = sorted(key for key in ledger['calls'] if key>cursor)[:limit+1]
                return dict(limits=limits,used=used,remaining={key:limits[key]-used[key] for key in limits},
                            deadline=deadline,cancelled=ledger['cancelled'],calls=[ledger['calls'][key] for key in keys[:limit]],
                            nextCursor=keys[limit-1] if len(keys)>limit else None)
            finally:
                conn.execute('ROLLBACK')


def validate_execution(conn):
    """Check durable grants during backup; never serialize them into public bundles."""
    from .runtime import get_run
    lease = metadata(conn,'researchLease')
    if lease is not None:
        fields(lease,TOKEN_KEYS,TOKEN_KEYS)
        require(all(text(lease[key]) for key in ('dbInstanceId','runId','ownerId')))
        require(type(lease['fence']) is int and lease['fence'] > 0)
        require(type(lease['leaseUntil']) in (float,int) and math.isfinite(lease['leaseUntil']) and lease['leaseUntil']>=0)
        require(lease['dbInstanceId'] == conn.execute("SELECT value FROM metadata WHERE key='dbInstanceId'").fetchone()[0])
        get_run(conn,lease['runId'])
    for row in conn.execute('SELECT run_id,payload FROM research_execution'):
        get_run(conn,row['run_id'])
        ledger = json.loads(row['payload'])
        fields(ledger,{'calls','grants','cancelled'},{'calls','grants','cancelled'})
        require(type(ledger['cancelled']) is bool and isinstance(ledger['calls'],dict) and isinstance(ledger['grants'],dict))
        for key,grant in ledger['grants'].items():
            require(text(key)); fields(grant,{'increments','deadline'},{'increments','deadline'})
            require(stamp(grant['deadline']))
            keys = {'searches','candidates','auxiliary','total'}
            fields(grant['increments'],keys,keys)
            require(all(type(value) is int and value>=0 for value in grant['increments'].values()))
        limits = dict(get_run(conn,row['run_id'])['request']['limits'])
        for grant in ledger['grants'].values():
            for key in limits:
                limits[key] += grant['increments'][key]
        # Validate every call shape before aggregating potentially untrusted identities.
        for key,call in ledger['calls'].items():
            keys = {'callId','kind','identity','reservedAt','expiresAt','status','resultHash'}
            fields(call,keys,keys)
            require(text(key) and call['callId']==key and call['kind'] in KINDS)
            require(text(call['identity']) if call['kind'] in ('discussion','auxiliary') else call['identity'] is None)
            require(all(type(call[k]) in (float,int) and math.isfinite(call[k]) for k in ('reservedAt','expiresAt')))
            require(0 <= call['reservedAt'] < call['expiresAt'] <= call['reservedAt']+30)
            require(call['status'] in ('reserved','completed'))
            require(hash_value(call['resultHash']) if call['status']=='completed' else call['resultHash'] is None)
        used = usage(list(ledger['calls'].values()))
        require(all(used[key] <= limits[key] for key in limits), 'Execution ledger exceeds authorized budget')


def reset_restored_execution(conn):
    """Restored copies are new execution identities, even if their fences are old."""
    import uuid
    from .storage import database_version
    if database_version(conn) != '2':
        return
    conn.execute('BEGIN IMMEDIATE')
    try:
        instance = str(uuid.uuid4())
        conn.execute("UPDATE metadata SET value=? WHERE key='dbInstanceId'",(instance,))
        lease = metadata(conn,'researchLease')
        if lease:
            lease.update(dbInstanceId=instance,fence=lease['fence']+1,leaseUntil=0)
            put_metadata(conn,'researchLease',lease)
        conn.execute('COMMIT')
    finally:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
