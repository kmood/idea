"""Prepare a public manifest first, then resume its dependency-ordered steps."""
from records.contracts import Fault,boundary,fields,require,text
from records.discovery import DiscoveryStore
from records.exchange import digest
from records.identity import IdentityStore
from records.publishing import ResearchPublisher,validate_manifest_progress
from records.service import ResearchStore

from .analysis import Analyzer
from .runner import value


def intent_for(request,operation_id):
    if request['action']=='create':
        record_id=request['record']['id'];expected=None
    else:
        record_id=request['recordId'];expected=request['expectedRevision']
    return dict(recordId=record_id,operationId=operation_id,requestHash=digest(request),
                expectedRevision=expected)


def evidence_record(claim,index,bindings,draft_hash):
    primary=claim['refs'][0]
    binding=bindings[primary['receiptId']]
    independence=[dict(groupId=digest(dict(receiptId=item['receiptId'],blockId=item['blockId'],
                                            actorId=item['actorId'],originId=item['originId'])),
                       basis=item['basis'],scope=item['scope']) for item in claim['independence']]
    observation=dict(receiptId=primary['receiptId'],blockIds=primary['blockIds'],replyIds=[],
                     independence=independence,precision=binding['precision'],
                     dateBasis=binding['dateBasis'],
                     paymentVerification=None if claim['payment'] is None else claim['payment']['basis'])
    record=dict(id=f'evidence:{draft_hash}:{index}',kind='Evidence',sourceId=binding['sourceId'],
                url=binding['originalUrl'],claim=claim['text'],summary=claim['text'],
                publishedAt=binding['publishedAt'],accessedAt=binding['fetchedAt'],
                nature=claim['nature'],level=claim['level'],
                paymentSignal=None if claim['payment'] is None else claim['payment']['stage'],
                rebutsClaim=claim['rebutsClaim'],observation=observation)
    if binding['precision']=='date':record['publishedDate']=binding['publishedDate']
    return record


class Publication:
    def __init__(self,runtime,run_id,token):
        self.runtime=runtime;self.run_id=run_id;self.token=token
        self.records=ResearchStore(runtime.db.path)
        self.publisher=ResearchPublisher(runtime)
        self.discovery=DiscoveryStore(runtime)
        self.identities=IdentityStore(runtime.db.path)

    @boundary
    def prepare(self,validated,locator):
        fields(validated,{'draft','draftHash','bindings'},{'draft','draftHash','bindings'})
        require(text(locator) and digest(validated['draft'])==validated['draftHash'])
        checked=value(Analyzer(self.runtime,self.run_id,self.token).validate(validated['draft']))
        require(checked==validated,'Analysis must be revalidated before preparing publication')
        draft=validated['draft'];candidate=value(self.discovery.candidate(self.run_id,draft['candidateId']))
        publication_hash=digest(dict(draftHash=validated['draftHash'],locator=locator))
        manifest_id='manifest:'+publication_hash
        existing=self.runtime.publication_plan(self.run_id,manifest_id,token=self.token)
        if existing['ok']:
            plan=existing['value']
        else:
            if existing['error']['code']!='NOT_FOUND':value(existing)
            supersedes=value(self.identities.latest_manifest(candidate['sourceId'],draft['candidateId'],manifest_id))
            plan=self.build_plan(validated,candidate,locator,manifest_id,supersedes)
            value(self.runtime.save_publication_plan(self.run_id,manifest_id,validated['draftHash'],plan,
                                                     token=self.token))
        manifest=self.ensure_manifest(plan)
        return dict(status='prepared',manifest=manifest)

    def build_plan(self,validated,candidate,locator,manifest_id,supersedes):
        draft=validated['draft'];draft_hash=validated['draftHash']
        bindings={item['receiptId']:item for item in validated['bindings']}
        require(len(bindings)==len(validated['bindings']))
        steps=[];evidence_ids=[]
        if draft['disposition'] in ('idea','trend','update'):
            claims=list(draft['claims'])+[counter | {'independence':[],'payment':None}
                                          for counter in draft['counterEvidence']]
            for index,claim in enumerate(claims,1):
                record=evidence_record(claim,index,bindings,draft_hash)
                request=dict(action='create',record=record,reason=draft['reason'])
                step_id=f'evidence:{index}'
                steps.append(dict(stepId=step_id,request=request,dependsOn=[]))
                evidence_ids.append(record['id'])

            content_id=None
            dependencies=[step['stepId'] for step in steps]
            if draft['disposition']=='idea':
                content=draft['content']
                content_id='idea:'+draft_hash
                record=dict(id=content_id,kind='Idea',title=content['title'],audience=content['audience'],
                            problem=content['problem'],earningHypothesis=content['earningHypothesis'],
                            industry=content['industry'],sideHustleTypes=content['sideHustleTypes'],
                            markets=content['markets'],researchStatus='待验证',evidenceIds=evidence_ids)
                content_request=dict(action='create',record=record,reason=draft['reason'])
                content_revision=1
            elif draft['disposition']=='trend':
                content=draft['content']
                content_id='trend:'+draft_hash
                record=dict(id=content_id,kind='Trend',title=content['title'],summary=content['summary'],
                            evidenceIds=evidence_ids,impact=content['impact'],questions=content['questions'])
                content_request=dict(action='create',record=record,reason=draft['reason'])
                content_revision=1
            else:
                target=draft['target'];current=value(self.records.read_record(target['recordId']))['record']
                require(current['revision']==target['revision'] and current['kind'] in ('Trend','Idea'))
                content_id=current['id'];patch={'evidenceIds':list(dict.fromkeys(current['evidenceIds']+evidence_ids))}
                if current['kind']=='Trend':patch['summary']=draft['content']['summary']
                content_request=dict(action='patch',recordId=content_id,expectedRevision=current['revision'],
                                     patch=patch,reason=draft['reason'])
                content_revision=current['revision']+1
            steps.append(dict(stepId='content',request=content_request,dependsOn=dependencies))
            record_refs=[dict(recordId=id,revision=1) for id in evidence_ids]
            record_refs.append(dict(recordId=content_id,revision=content_revision))
        else:
            record_refs=[]

        outcome_id='outcome:'+draft_hash
        outcome=dict(id=outcome_id,kind='ResearchArtifact',artifactType='CandidateOutcome',data=dict(
            runId=self.run_id,candidateId=draft['candidateId'],sourceId=candidate['sourceId'],locator=locator,
            status=draft['disposition'],reason=draft['reason'],nextCondition=draft['nextCondition'],
            recordRefs=record_refs))
        outcome_request=dict(action='create',record=outcome,reason=draft['reason'])
        steps.append(dict(stepId='outcome',request=outcome_request,
                          dependsOn=[step['stepId'] for step in steps]))

        public_steps=[]
        for step in steps:
            request=step['request'];target=request['record']['id'] if request['action']=='create' else request['recordId']
            public_steps.append(dict(stepId=step['stepId'],targetId=target,
                                     operationId='publish:'+manifest_id+':'+step['stepId'],
                                     requestHash=digest(request),
                                     expectedRevision=None if request['action']=='create' else request['expectedRevision'],
                                     dependsOn=step['dependsOn'],result=None))
        manifest=dict(id=manifest_id,kind='ResearchArtifact',artifactType='PublicationManifest',data=dict(
            runId=self.run_id,candidateId=draft['candidateId'],sourceId=candidate['sourceId'],
            steps=public_steps,supersedes=supersedes))
        manifest_request=dict(action='create',record=manifest,reason='Prepare validated publication steps')
        return dict(manifestId=manifest_id,draftHash=draft_hash,manifestRequest=manifest_request,
                    steps=[dict(stepId=step['stepId'],request=step['request']) for step in steps])

    def ensure_manifest(self,plan):
        request=plan['manifestRequest'];manifest_id=plan['manifestId']
        intent_id='publication:'+manifest_id+':manifest'
        intent=intent_for(request,'publish:'+manifest_id)
        value(self.runtime.save_intent(self.run_id,intent_id,intent,token=self.token))
        value(self.publisher.publish_step(self.run_id,self.token,intent_id,request))
        manifest=value(self.records.read_record(manifest_id))['record']
        validate_manifest_progress(plan,manifest)
        return manifest

    @boundary
    def resume(self,manifest_id,max_steps=None):
        require(text(manifest_id) and (max_steps is None or (type(max_steps) is int and max_steps>=0)))
        plan=value(self.runtime.publication_plan(self.run_id,manifest_id,token=self.token))
        manifest=self.ensure_manifest(plan);requests={step['stepId']:step['request'] for step in plan['steps']}
        completed_now=0
        for public_step in manifest['data']['steps']:
            if public_step['result'] is not None:continue
            if max_steps is not None and completed_now>=max_steps:break
            require(all(next(step for step in manifest['data']['steps'] if step['stepId']==dependency)['result']
                        is not None for dependency in public_step['dependsOn']))
            request=requests[public_step['stepId']]
            intent_id='publication:'+manifest_id+':'+public_step['stepId']
            intent=intent_for(request,public_step['operationId'])
            value(self.runtime.save_intent(self.run_id,intent_id,intent,token=self.token))
            result=value(self.publisher.publish_step(self.run_id,self.token,intent_id,request))['result']
            updated_steps=[step | ({'result':result} if step['stepId']==public_step['stepId'] else {})
                           for step in manifest['data']['steps']]
            patch_request=dict(action='patch',recordId=manifest_id,expectedRevision=manifest['revision'],
                               patch={'data':manifest['data'] | {'steps':updated_steps}},
                               reason='Confirm completed publication step')
            confirm_id='publication:'+manifest_id+':confirm:'+public_step['stepId']
            confirm_intent=intent_for(patch_request,'confirm:'+manifest_id+':'+public_step['stepId'])
            value(self.runtime.save_intent(self.run_id,confirm_id,confirm_intent,token=self.token))
            manifest=value(self.publisher.publish_step(self.run_id,self.token,confirm_id,patch_request))['record']
            completed_now+=1
        complete=all(step['result'] is not None for step in manifest['data']['steps'])
        outcome=next(step for step in manifest['data']['steps'] if step['stepId']=='outcome')
        return dict(status='complete' if complete else 'partial',manifest=manifest,
                    outcomeId=outcome['targetId'] if complete else None)
