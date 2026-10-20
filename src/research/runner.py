"""Bounded run ownership and recovery. Agent search handoff is available through bridge()."""
import time
from records.contracts import Fault, boundary
from records.runtime import ResearchRuntimeStore
from .contracts import new_request


def value(result):
    if not result['ok']:
        error = result['error']
        raise Fault(error['code'],error['message'])
    return result['value']


class Runner:
    def __init__(self,path,clock=None):
        self.clock = clock or time.time
        self.store = ResearchRuntimeStore(path,clock=self.clock)

    def bridge(self,run_id,token):
        from .bridge import AgentBridge
        return AgentBridge(self.store,run_id,token)

    def publication(self,run_id,token):
        from .publication import Publication
        return Publication(self.store,run_id,token)

    def progress(self,run_id,token):
        from .progress import Progress
        return Progress(self.store,run_id,token)

    def coverage(self,run_id,token):
        from .coverage import Coverage
        return Coverage(self.store,run_id,token)

    @boundary
    def start(self,run_id,owner_id,source_ids,queries,limits=None):
        request = new_request(source_ids,queries,self.clock(),limits)
        previous = self.store.inspect_run(run_id)
        if previous['ok']:
            request['deadline'] = previous['value']['run']['request']['deadline']
        elif previous['error']['code'] != 'NOT_FOUND':
            value(previous)
        value(self.store.begin(run_id,request))
        return value(self.resume(run_id,owner_id))

    @boundary
    def resume(self,run_id,owner_id):
        token = value(self.store.execution.acquire(run_id,owner_id))
        state = value(self.store.execution.inspect(run_id))
        reason = ('cancelled' if state['cancelled'] else 'deadline' if self.clock()>=state['deadline']
                  else 'budget' if state['remaining']['total']==0 else None)
        return dict(runId=run_id,status='partial' if reason else 'ready',reason=reason,token=token,state=state)
