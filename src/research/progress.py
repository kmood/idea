"""Gap-preserving source progress and bounded retry decisions."""
from records.contracts import Fault,boundary,require,string_list,text
from records.artifacts import ref
from records.exchange import digest
from records.progress import ProgressStore
from records.publishing import ResearchPublisher
from records.service import ResearchStore

from .publication import intent_for
from .runner import value


class Progress:
    def __init__(self,runtime,run_id,token):
        self.runtime=runtime;self.run_id=run_id;self.token=token
        self.local=ProgressStore(runtime);self.records=ResearchStore(runtime.db.path)
        self.publisher=ResearchPublisher(runtime)

    def current(self,source_id):
        return value(self.local.load(self.run_id,source_id,token=self.token))

    def save(self,state,before=None):
        operation='state:'+digest(dict(before=before,after=state))
        return value(self.local.save(self.run_id,state['sourceId'],state,operation,
                                     token=self.token))

    @boundary
    def discover(self,source_id,order,positions,discovered,overlap_strategy,*,cursor_valid=True):
        require(text(source_id) and order in ('ordered','unordered'))
        require(string_list(positions) and bool(positions) and text(discovered) and text(overlap_strategy))
        require(type(cursor_valid) is bool)
        loaded=self.local.load(self.run_id,source_id,token=self.token)
        if loaded['ok']:
            state=loaded['value'];before=digest(state)
            require(state['order']==order and state['overlapStrategy']==overlap_strategy)
            state=state | {'positions':state['positions']+[p for p in positions if p not in state['positions']],
                           'cursorInvalid':not cursor_valid}
            if cursor_valid:state['discovered']=discovered
        else:
            if loaded['error']['code']!='NOT_FOUND':value(loaded)
            before=None
            state=dict(sourceId=source_id,order=order,positions=list(positions),
                       discovered=discovered if cursor_valid else None,completed=None,gaps=[],processed=[],
                       overlapStrategy=overlap_strategy,attempts={},cursorInvalid=not cursor_valid,lastReceipt=None)
        state=self.save(state,before)
        checkpoint=None if not cursor_valid else self.sync(state)
        return dict(action='restart_with_overlap' if not cursor_valid else 'continue',state=state,
                    checkpoint=checkpoint)

    @boundary
    def begin_attempt(self,source_id,position):
        state=self.current(source_id);before=digest(state);require(position in state['positions'])
        attempt=state['attempts'].get(position,dict(count=0,inFlight=False,retryable=True,
                                                     retryAt=None,lastError=None))
        if attempt['inFlight']:raise Fault('ATTEMPT_PENDING','Record the current attempt result first')
        if attempt['count']>=2 or (attempt['count'] and not attempt['retryable']):
            raise Fault('RETRY_EXHAUSTED','At most one retry is allowed')
        now=self.runtime.execution.clock()
        if attempt['retryAt'] is not None and now<attempt['retryAt']:
            raise Fault('RATE_LIMIT','Wait before retrying',retryAt=attempt['retryAt'])
        attempt=attempt | {'count':attempt['count']+1,'inFlight':True}
        state['attempts']=state['attempts'] | {position:attempt};self.save(state,before)
        return dict(attempt=attempt['count'],position=position)

    @boundary
    def fail(self,source_id,position,code,*,retryable,retry_at=None):
        require(text(code) and len(code)<=200 and type(retryable) is bool)
        require(retry_at is None or type(retry_at) in (int,float))
        state=self.current(source_id);before=digest(state);attempt=state['attempts'].get(position)
        require(attempt is not None and attempt['inFlight'],'Begin the attempt before recording failure')
        attempt=attempt | dict(inFlight=False,retryable=retryable,retryAt=retry_at,lastError=code)
        state['attempts']=state['attempts'] | {position:attempt}
        state['gaps']=sorted(set(state['gaps'])|{position},key=state['positions'].index)
        state=self.save(state,before);checkpoint=self.sync(state)
        now=self.runtime.execution.clock()
        allowed=retryable and attempt['count']<2 and (retry_at is None or retry_at<=now)
        return dict(retryAllowed=allowed,state=state,checkpoint=checkpoint)

    @boundary
    def settle(self,source_id,position,outcome_id,last_receipt=None):
        require(text(outcome_id));state=self.current(source_id);before=digest(state)
        require(position in state['positions'])
        outcome=value(self.records.read_record(outcome_id))['record']
        require(outcome['kind']=='ResearchArtifact' and outcome['artifactType']=='CandidateOutcome' and
                not outcome['archived'] and outcome['data']['runId']==self.run_id and
                outcome['data']['sourceId']==source_id and outcome['data']['candidateId']==position,
                'Checkpoint requires the matching persisted outcome')
        if last_receipt is not None:
            ref(last_receipt)
            receipt=value(self.records.read_record(last_receipt['recordId'],last_receipt['revision']))['record']
            require(receipt['kind']=='ResearchArtifact' and receipt['artifactType']=='ReadReceipt' and
                    receipt['data']['sourceId']==source_id)
        state['processed']=sorted(set(state['processed'])|{position},key=state['positions'].index)
        state['gaps']=[item for item in state['gaps'] if item!=position]
        if state['order']=='ordered':
            completed=None
            for item in state['positions']:
                if item not in state['processed']:break
                completed=item
            state['completed']=completed
        if position in state['attempts']:
            state['attempts'][position]=state['attempts'][position] | {
                'inFlight':False,'retryable':False,'retryAt':None,'lastError':None}
        state['lastReceipt']=last_receipt
        state=self.save(state,before);return dict(state=state,checkpoint=self.sync(state))

    @boundary
    def sync_checkpoint(self,source_id):
        state=self.current(source_id)
        return dict(state=state,checkpoint=self.sync(state))

    def checkpoint_data(self,state):
        return dict(sourceId=state['sourceId'],order=state['order'],discovered=state['discovered'],
                    completed=state['completed'],gaps=state['gaps'],processed=state['processed'],
                    overlapStrategy=state['overlapStrategy'],lastReceipt=state['lastReceipt'])

    def sync(self,state):
        record_id='checkpoint:'+self.run_id+':'+state['sourceId'];data=self.checkpoint_data(state)
        existing=self.records.read_record(record_id)
        if existing['ok']:
            current=existing['value']['record']
            require(current['kind']=='ResearchArtifact' and current['artifactType']=='SourceCheckpoint')
            if current['data']==data:return current
            request=dict(action='patch',recordId=record_id,expectedRevision=current['revision'],
                         patch={'data':data},reason='Confirm source sampling progress')
        else:
            if existing['error']['code']!='NOT_FOUND':value(existing)
            record=dict(id=record_id,kind='ResearchArtifact',artifactType='SourceCheckpoint',data=data)
            request=dict(action='create',record=record,reason='Initialize source sampling progress')
        key=digest(request);intent_id='progress:'+state['sourceId']+':'+key
        value(self.runtime.save_intent(self.run_id,intent_id,intent_for(request,'checkpoint:'+key),
                                       token=self.token))
        return value(self.publisher.publish_step(self.run_id,self.token,intent_id,request))['record']
