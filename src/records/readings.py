"""Reader-owned immutable receipts and local cache pointers, saved atomically."""
import json
import time
from contextlib import closing
from .artifacts import _READER_AUTHORITY,hash_value
from .contracts import Fault,boundary,encoded,fields,now,require,text,validate_record
from .exchange import digest
from .storage import get,references,save


class ReadingStore:
    def __init__(self,runtime):
        self.runtime=runtime
        with closing(runtime.db.connect()) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS research_readings(receipt_id TEXT PRIMARY KEY REFERENCES research_records(id),payload TEXT NOT NULL)')

    @boundary
    def capture(self,run_id,token,data,cache_key):
        require(hash_value(cache_key))
        identity=dict(action='read',sourceId=data['sourceId'],finalUrl=data['finalUrl'],fingerprint=data['fingerprint'])
        receipt_id='read:'+digest(identity);operation_id='capture:'+receipt_id
        def action(conn):
            self.runtime.execution.guard(conn,run_id,token)
            require(data['runId']==run_id)
            row=conn.execute('SELECT payload FROM research_records WHERE id=?',(receipt_id,)).fetchone()
            if row:
                receipt=json.loads(row[0])
                require(receipt['kind']=='ResearchArtifact' and receipt['artifactType']=='ReadReceipt')
                require(all(receipt['data'][key]==data[key] for key in ('sourceId','finalUrl','fingerprint')))
            else:
                timestamp=now()
                receipt=dict(id=receipt_id,kind='ResearchArtifact',artifactType='ReadReceipt',data=data,
                             schemaVersion=1,revision=1,createdAt=timestamp,updatedAt=timestamp,archived=False,mergedInto=None)
                validate_record(receipt);references(conn,receipt)
                save(conn,receipt,None,operation_id,'created','Public Reader observed visible content',authority=_READER_AUTHORITY)
                conn.execute('INSERT INTO operations VALUES (?,?,?,?)',('research',operation_id,digest(identity),encoded(receipt)))
            local=dict(cacheKey=cache_key,runId=run_id,expiresAt=time.time()+7*86400)
            conn.execute('INSERT INTO research_readings VALUES (?,?) ON CONFLICT(receipt_id) DO UPDATE SET payload=excluded.payload',(receipt_id,encoded(local)))
            return dict(receipt=receipt,unchanged=row is not None)
        return self.runtime.execution.transaction(action)

    @boundary
    def pointer(self,receipt_id):
        require(text(receipt_id))
        with closing(self.runtime.db.connect()) as conn:
            row=conn.execute('SELECT payload FROM research_readings WHERE receipt_id=?',(receipt_id,)).fetchone()
            if row is None:raise Fault('CACHE_MISSING','Read the original public page again')
            result=json.loads(row[0])
            if result['expiresAt']<=time.time():raise Fault('CACHE_EXPIRED','Read the original public page again')
            return result


def validate_readings(conn):
    import math
    from .runtime import get_run
    for row in conn.execute('SELECT receipt_id,payload FROM research_readings'):
        value=json.loads(row['payload'])
        fields(value,{'cacheKey','runId','expiresAt'},{'cacheKey','runId','expiresAt'})
        require(hash_value(value['cacheKey']) and text(value['runId']))
        require(type(value['expiresAt']) in (float,int) and math.isfinite(value['expiresAt']) and value['expiresAt']>=0)
        get_run(conn,value['runId'])
        record=get(conn,row['receipt_id'])
        require(record['kind']=='ResearchArtifact' and record['artifactType']=='ReadReceipt')
