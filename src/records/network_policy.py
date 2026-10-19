"""Local robots cache and source/origin pacing, shared across runs and restarts."""
import json
import math
from contextlib import closing
from urllib.parse import urlsplit
from .contracts import Fault,boundary,encoded,fields,require,text,valid_url
from .storage import get


def validate_policy(value):
    fields(value,{'nextAt','robots'},{'nextAt','robots'})
    require(type(value['nextAt']) in (int,float) and math.isfinite(value['nextAt']) and value['nextAt']>=0)
    cached=value['robots']
    if cached is not None:
        keys={'fetchedAt','expiresAt','status','body','delay'}
        fields(cached,keys,keys)
        require(all(type(cached[k]) in (int,float) and math.isfinite(cached[k]) for k in ('fetchedAt','expiresAt','delay')))
        require(0<=cached['fetchedAt']<cached['expiresAt']<=cached['fetchedAt']+86400 and cached['delay']>=3)
        require(type(cached['status']) is int and 100<=cached['status']<=599)
        require(isinstance(cached['body'],str) and len(cached['body'].encode('utf-8'))<=65536)


class NetworkPolicyStore:
    def __init__(self, runtime):
        self.runtime=runtime;self.execution=runtime.execution
        with closing(runtime.db.connect()) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS research_network(key TEXT PRIMARY KEY,payload TEXT NOT NULL)')

    def row(self,conn,key):
        row=conn.execute('SELECT payload FROM research_network WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else dict(nextAt=0,robots=None)

    def save(self,conn,key,value):
        validate_policy(value)
        conn.execute('INSERT INTO research_network VALUES (?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload',(key,encoded(value)))

    def keys(self,origin,source_id):
        require(valid_url(origin) and text(source_id))
        parsed=urlsplit(origin)
        require(not parsed.username and not parsed.password and not parsed.path and not parsed.query and not parsed.fragment)
        return 'origin:'+origin,'source:'+source_id

    @boundary
    def cached(self,origin,source_id):
        origin_key,_=self.keys(origin,source_id)
        with closing(self.runtime.db.connect()) as conn:
            require(get(conn,source_id)['kind']=='Source')
            value=self.row(conn,origin_key)['robots']
            return value if value and value['expiresAt']>self.execution.clock() else None

    @boundary
    def permit(self,origin,source_id,run_id,token,delay=3):
        keys=self.keys(origin,source_id)
        require(type(delay) in (int,float) and math.isfinite(delay) and delay>=3)
        def action(conn):
            current=self.execution.guard(conn,run_id,token)
            require(get(conn,source_id)['kind']=='Source')
            rows=[self.row(conn,key) for key in keys]
            next_at=max(row['nextAt'] for row in rows)
            if current<next_at:
                raise Fault('RATE_LIMIT','Wait before another source request',retryAt=next_at)
            for key,row in zip(keys,rows):
                row['nextAt']=current+delay;self.save(conn,key,row)
            return dict(permitted=True)
        return self.execution.transaction(action)

    @boundary
    def remember(self,origin,source_id,run_id,token,status,body,delay=3,ttl=86400):
        keys=self.keys(origin,source_id)
        def action(conn):
            current=self.execution.guard(conn,run_id,token)
            require(get(conn,source_id)['kind']=='Source')
            for key in keys:
                row=self.row(conn,key)
                row['nextAt']=max(row['nextAt'],current+delay)
                if key==keys[0]:
                    row['robots']=dict(fetchedAt=current,expiresAt=current+ttl,status=status,body=body,delay=delay)
                self.save(conn,key,row)
            return dict(saved=True)
        return self.execution.transaction(action)


    @boundary
    def postpone(self,origin,source_id,run_id,token,delay):
        keys=self.keys(origin,source_id)
        require(type(delay) in (int,float) and math.isfinite(delay) and delay>=3)
        def action(conn):
            current=self.execution.guard(conn,run_id,token)
            require(get(conn,source_id)['kind']=='Source')
            for key in keys:
                row=self.row(conn,key);row['nextAt']=max(row['nextAt'],current+delay)
                self.save(conn,key,row)
            return dict(saved=True)
        return self.execution.transaction(action)


def validate_network(conn):
    for row in conn.execute('SELECT key,payload FROM research_network'):
        require(text(row['key']) and row['key'].startswith(('origin:','source:')))
        validate_policy(json.loads(row['payload']))
