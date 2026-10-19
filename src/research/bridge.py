"""Agent handoff: tool results are discoveries, never proof of reading."""
from records.contracts import Fault,boundary,require
from records.discovery import DiscoveryStore
from records.service import ResearchStore
from .runner import value


class AgentBridge:
    def __init__(self,runtime,run_id,token):
        self.runtime=runtime;self.run_id=run_id;self.token=token
        self.discovery=DiscoveryStore(runtime)

    @boundary
    def register_source(self,source,operation_id):
        require(isinstance(source,dict) and source.get('kind')=='Source')
        require(source.get('accessStatus')=='untried' and source.get('lastAttempt') is None and source.get('lastSuccess') is None,
                'Discovery alone cannot establish successful access')
        def guard(conn):
            execution=self.runtime.execution;current=execution.guard(conn,self.run_id,self.token)
            ledger=execution.ledger(conn,self.run_id)
            _,deadline=execution.limits(conn,self.run_id,ledger)
            if ledger['cancelled']:raise Fault('CANCELLED')
            if current>=deadline:raise Fault('DEADLINE_EXCEEDED')
        return value(ResearchStore(self.runtime.db.path).create_research(source,operation_id,guard=guard))

    @boundary
    def request(self,call_id,query,*,tool=None):
        if tool is None:
            return dict(status='blocked',reason='No Agent search tool is available',callId=None)
        return value(self.discovery.request(self.run_id,self.token,call_id,dict(query=query,tool=tool)))

    def submit(self,call_id,result):
        return self.discovery.submit(self.run_id,self.token,call_id,result)

    def inspect(self,cursor='',limit=20):
        return self.discovery.inspect(self.run_id,cursor,limit)

    def inspect_searches(self,cursor='',limit=20):
        return self.discovery.inspect(self.run_id,cursor,limit,searches=True)
