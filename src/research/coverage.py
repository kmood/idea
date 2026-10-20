"""Validate an evidence-grounded coverage review and publish the recommendation."""
from records.artifacts import ref
from records.contracts import boundary,encoded,fields,require,string_list,text
from records.exchange import digest
from records.identity import IdentityStore
from records.publishing import ResearchPublisher
from records.service import ResearchStore

from .publication import intent_for
from .runner import value

DIMENSIONS={'industries','audiences','markets','sideHustleTypes','sourceTypes','readScopes'}
COVERAGE_KEYS=DIMENSIONS | {'sustainableSources','alternatives','duplicateHandling','patrolPlan',
                            'channelAdjustment'}


class Coverage:
    def __init__(self,runtime,run_id,token):
        self.runtime=runtime;self.run_id=run_id;self.token=token
        self.records=ResearchStore(runtime.db.path);self.identities=IdentityStore(runtime.db.path)
        self.publisher=ResearchPublisher(runtime)

    def authorize(self):
        self.runtime.execution.transaction(lambda conn:self.runtime.execution.guard(
            conn,self.run_id,self.token))

    @boundary
    def publish(self,draft):
        require(len(encoded(draft).encode())<=256*1024,'Coverage review is too large')
        keys={'runIds','sourceRefs','evidenceRefs','gaps','qualityReasons','recommendation','reason','coverage'}
        fields(draft,keys,keys);self.authorize()
        require(string_list(draft['runIds']) and 0<len(draft['runIds'])<=20)
        require(string_list(draft['gaps']) and bool(draft['gaps']))
        require(string_list(draft['qualityReasons']) and bool(draft['qualityReasons']))
        require(draft['recommendation'] in ('concentrate','incremental','adjust') and text(draft['reason']))
        source_refs=self.validate_refs(draft['sourceRefs'],'Source')
        evidence_refs=self.validate_refs(draft['evidenceRefs'],'Evidence',allow_empty=True)
        runs=[value(self.runtime.inspect_run(run_id))['run'] for run_id in draft['runIds']]
        require([run['createdAt'] for run in runs]==sorted(run['createdAt'] for run in runs),
                'Reviewed runs must be chronological')
        source_ids={item['id'] for item in source_refs}
        read_scopes=set();readable_source_ids=set()
        for evidence in evidence_refs:
            require('observation' in evidence,'Coverage evidence requires Reader provenance')
            receipt=value(self.records.read_record(evidence['observation']['receiptId']))['record']
            observation=evidence['observation'];receipt_data=receipt['data']
            require(receipt['kind']=='ResearchArtifact' and receipt['artifactType']=='ReadReceipt' and
                    not receipt['archived'] and
                    receipt['data']['runId'] in draft['runIds'] and
                    receipt['data']['sourceId'] in source_ids and evidence['sourceId'] in source_ids,
                    'Coverage evidence must belong to a reviewed run and source')
            require(set(observation['blockIds'])<={item['blockId'] for item in receipt_data['blocks']} and
                    evidence['url'] in (receipt_data['originalUrl'],receipt_data['finalUrl']) and
                    evidence['accessedAt']==receipt_data['fetchedAt'],
                    'Coverage evidence must match its Reader receipt')
            read_scopes.add(receipt_data['visibleScope'])
            readable_source_ids.add(receipt_data['sourceId'])
        coverage=draft['coverage'];fields(coverage,COVERAGE_KEYS,COVERAGE_KEYS)
        for key in DIMENSIONS:require(string_list(coverage[key]) and bool(coverage[key]))
        require(string_list(coverage['sustainableSources']) and string_list(coverage['alternatives']))
        require(text(coverage['duplicateHandling']) and text(coverage['patrolPlan']))
        require(coverage['channelAdjustment'] is None or text(coverage['channelAdjustment']))
        require(set(coverage['sustainableSources'])<=readable_source_ids and
                set(coverage['sourceTypes'])<={item['profile']['sourceType'] for item in source_refs
                                               if 'profile' in item} and
                set(coverage['readScopes'])<=read_scopes,
                'Coverage dimensions must match referenced sources and reading receipts')
        counts=value(self.identities.evidence_counts(draft['runIds']))
        trailing=[]
        for run_id in reversed(draft['runIds']):
            if counts[run_id]:break
            trailing.append(run_id)
        trailing.reverse()
        if len(trailing)>=3:
            require(draft['recommendation']=='adjust' and text(coverage['channelAdjustment']),
                    'Three rounds without new evidence require a channel adjustment')
        if draft['recommendation']=='adjust':
            require(text(coverage['channelAdjustment']),'Channel adjustment requires a concrete change')
        if draft['recommendation']=='incremental':
            require(bool(evidence_refs) and bool(coverage['sustainableSources']) and
                    bool(coverage['alternatives']) and bool(draft['gaps']),
                    'Incremental readiness needs traceable evidence, sustainable sources, alternatives and named gaps')
        public_coverage=coverage | {'noNewEvidenceRuns':trailing}
        data=dict(runIds=draft['runIds'],sourceRefs=draft['sourceRefs'],evidenceRefs=draft['evidenceRefs'],
                  gaps=draft['gaps'],qualityReasons=draft['qualityReasons'],
                  recommendation=draft['recommendation'],reason=draft['reason'],coverage=public_coverage)
        record_id='coverage:'+digest(data)
        record=dict(id=record_id,kind='ResearchArtifact',artifactType='CoverageReview',data=data)
        request=dict(action='create',record=record,reason=draft['reason'])
        intent_id='coverage:'+digest(request)
        value(self.runtime.save_intent(self.run_id,intent_id,intent_for(request,'publish:'+record_id),
                                       token=self.token))
        published=value(self.publisher.publish_step(self.run_id,self.token,intent_id,request))['record']
        return dict(record=published,recommendation=draft['recommendation'])

    def validate_refs(self,refs,kind,allow_empty=False):
        require(isinstance(refs,list) and len(refs)<=100 and (allow_empty or bool(refs)))
        records=[];seen=set()
        for item in refs:
            ref(item);key=(item['recordId'],item['revision']);require(key not in seen);seen.add(key)
            record=value(self.records.read_record(*key))['record']
            require(record['kind']==kind and not record['archived'])
            records.append(record)
        return records
