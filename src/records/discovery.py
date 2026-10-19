"""Durable local search handoffs and candidate queue; never public evidence."""
import json
from contextlib import closing
from .contracts import Fault,boundary,encoded,fields,require,text,valid_url
from .exchange import digest
from .storage import get
from .runtime import get_run

TABLES=('research_searches','research_candidates')


def validate_search(request):
    fields(request,{'query','tool'},{'query','tool'})
    require(text(request['query']) and len(request['query'])<=2000)
    require(text(request['tool']) and len(request['tool'])<=200)


def validate_result(result):
    keys={'status','reason','discoveries'};fields(result,keys,keys)
    require(result['status'] in ('completed','blocked','failed'))
    require(result['reason'] is None or (text(result['reason']) and len(result['reason'])<=1000))
    require(isinstance(result['discoveries'],list) and len(result['discoveries'])<=100)
    if result['status']!='completed':
        require(text(result['reason']) and not result['discoveries'])
    for item in result['discoveries']:
        keys={'sourceId','url','title','snippet'};fields(item,keys,keys)
        require(text(item['sourceId']) and len(item['sourceId'])<=500 and valid_url(item['url']) and len(item['url'])<=8192)
        require(text(item['title']) and len(item['title'])<=1000)
        require(isinstance(item['snippet'],str) and len(item['snippet'])<=4000)


def candidate_id(item):
    return 'candidate:'+digest(dict(sourceId=item['sourceId'],url=item['url']))


class DiscoveryStore:
    def __init__(self,runtime):
        self.runtime=runtime
        with closing(runtime.db.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            for table,key in zip(TABLES,('call_id','candidate_id')):
                conn.execute(f'CREATE TABLE IF NOT EXISTS {table}(run_id TEXT NOT NULL REFERENCES research_runs(run_id),{key} TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(run_id,{key}))')
            conn.execute('COMMIT')

    @boundary
    def request(self,run_id,token,call_id,request):
        validate_search(request)
        def action(conn):
            execution=self.runtime.execution
            execution.guard(conn,run_id,token)
            row=conn.execute('SELECT payload FROM research_searches WHERE run_id=? AND call_id=?',(run_id,call_id)).fetchone()
            if row and json.loads(row[0])['request']!=request:
                raise Fault('IDEMPOTENCY_CONFLICT','Call ID is bound to another search')
            grant=execution.reserve_in(conn,run_id,token,call_id,'search')
            if not row:
                payload=dict(request=request,result=None)
                conn.execute('INSERT INTO research_searches VALUES (?,?,?)',(run_id,call_id,encoded(payload)))
            result=json.loads(row[0])['result'] if row else None
            return dict(status=result['status'] if result is not None else 'awaiting_agent',callId=call_id,request=request,expiresAt=grant['expiresAt'])
        return self.runtime.execution.transaction(action)

    @boundary
    def submit(self,run_id,token,call_id,result):
        require(text(call_id));validate_result(result)
        def action(conn):
            execution=self.runtime.execution;execution.guard(conn,run_id,token)
            row=conn.execute('SELECT payload FROM research_searches WHERE run_id=? AND call_id=?',(run_id,call_id)).fetchone()
            require(row is not None,'Search must be requested before submission')
            search=json.loads(row[0])
            execution.finish_in(conn,run_id,token,call_id,digest(result))
            if search['result'] is not None:
                require(search['result']==result)
                return dict(status=result['status'],candidateIds=list(dict.fromkeys(candidate_id(item) for item in result['discoveries'])))
            for item in result['discoveries']:
                source=get(conn,item['sourceId'])
                require(source['kind']=='Source' and not source['archived'] and source['mergedInto'] is None,'Register an active source before queueing')
                key=candidate_id(item)
                payload=dict(candidateId=key,sourceId=item['sourceId'],url=item['url'],status='discovered',firstCallId=call_id)
                conn.execute('INSERT INTO research_candidates VALUES (?,?,?) ON CONFLICT(run_id,candidate_id) DO NOTHING',(run_id,key,encoded(payload)))
            search['result']=result
            conn.execute('UPDATE research_searches SET payload=? WHERE run_id=? AND call_id=?',(encoded(search),run_id,call_id))
            return dict(status=result['status'],candidateIds=list(dict.fromkeys(candidate_id(item) for item in result['discoveries'])))
        return self.runtime.execution.transaction(action)

    @boundary
    def inspect(self,run_id,cursor='',limit=20,*,searches=False):
        require(isinstance(cursor,str) and type(limit) is int and 1<=limit<=100)
        table,key=('research_searches','call_id') if searches else ('research_candidates','candidate_id')
        with closing(self.runtime.db.connect()) as conn:
            conn.execute('BEGIN');get_run(conn,run_id)
            rows=conn.execute(f'SELECT {key},payload FROM {table} WHERE run_id=? AND {key}>? ORDER BY {key} LIMIT ?',(run_id,cursor,limit+1)).fetchall()
            items=[json.loads(row['payload']) | ({'callId':row[key]} if searches else {}) for row in rows[:limit]]
            return dict(items=items,nextCursor=rows[limit-1][key] if len(rows)>limit else None)


def validate_discovery(conn):
    for row in conn.execute('SELECT * FROM research_searches'):
        get_run(conn,row['run_id']);require(text(row['call_id']))
        search=json.loads(row['payload']);fields(search,{'request','result'},{'request','result'})
        validate_search(search['request'])
        ledger=conn.execute('SELECT payload FROM research_execution WHERE run_id=?',(row['run_id'],)).fetchone()
        require(ledger is not None)
        call=json.loads(ledger[0])['calls'].get(row['call_id']);require(call is not None and call['kind']=='search')
        if search['result'] is None:require(call['status']=='reserved')
        else:
            validate_result(search['result'])
            require(call['status']=='completed' and call['resultHash']==digest(search['result']))
            for item in search['result']['discoveries']:
                require(get(conn,item['sourceId'])['kind']=='Source')
                require(conn.execute('SELECT 1 FROM research_candidates WHERE run_id=? AND candidate_id=?',(row['run_id'],candidate_id(item))).fetchone() is not None)
    for row in conn.execute('SELECT * FROM research_candidates'):
        value=json.loads(row['payload']);keys={'candidateId','sourceId','url','status','firstCallId'};fields(value,keys,keys)
        require(value['candidateId']==row['candidate_id']==candidate_id(value) and value['status']=='discovered')
        require(get(conn,value['sourceId'])['kind']=='Source')
        search=conn.execute('SELECT payload FROM research_searches WHERE run_id=? AND call_id=?',(row['run_id'],value['firstCallId'])).fetchone()
        require(search is not None)
        result=json.loads(search[0])['result'];require(result is not None)
        require(any(candidate_id(item)==value['candidateId'] for item in result['discoveries']))
