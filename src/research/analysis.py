"""Check read provenance and evidence prerequisites, not real-world truth."""
import json
from urllib.parse import urlsplit
from records.contracts import Fault,boundary,encoded,fields,require,text,string_list
from records.service import ResearchStore
from records.discovery import DiscoveryStore
from records.exchange import digest
from .contracts import validate_draft
from .reader import Reader
from .runner import value


class Analyzer:
    def __init__(self,runtime,run_id,token):
        self.runtime=runtime;self.run_id=run_id;self.token=token
        self.records=ResearchStore(runtime.db.path)
        self.discovery=DiscoveryStore(runtime)
        self.reader=Reader(runtime,run_id,token)

    def authorize(self):
        def check(conn):
            execution=self.runtime.execution;current=execution.guard(conn,self.run_id,self.token)
            ledger=execution.ledger(conn,self.run_id)
            if ledger['cancelled']:raise Fault('CANCELLED')
            _,deadline=execution.limits(conn,self.run_id,ledger)
            if current>=deadline:raise Fault('DEADLINE_EXCEEDED')
        self.runtime.execution.transaction(check)

    @boundary
    def validate(self,draft):
        serialized=encoded(draft);require(len(serialized.encode())<=256*1024,'Draft is too large')
        draft=json.loads(serialized);validate_draft(draft);self.authorize()
        candidate=value(self.discovery.candidate(self.run_id,draft['candidateId']))
        receipts={}

        def references(refs):
            require(isinstance(refs,list) and 0<len(refs)<=100)
            pairs=set()
            for ref in refs:
                fields(ref,{'receiptId','blockIds'},{'receiptId','blockIds'})
                require(text(ref['receiptId']) and string_list(ref['blockIds']) and bool(ref['blockIds']))
                rid=ref['receiptId']
                if rid not in receipts:
                    record=value(self.records.read_record(rid))['record']
                    require(record['kind']=='ResearchArtifact' and record['artifactType']=='ReadReceipt' and not record['archived'])
                    data=record['data'];require(data['status'] in ('readable','partial'))
                    cached=value(self.reader.cached(rid))
                    require(digest(cached)==data['fingerprint'],'Cache does not match receipt')
                    require({b['blockId'] for b in cached['blocks']}=={b['blockId'] for b in data['blocks']})
                    receipts[rid]=data
                allowed={b['blockId'] for b in receipts[rid]['blocks']}
                require(set(ref['blockIds'])<=allowed,'Unobserved blocks or replies cannot be evidence')
                pairs.update((rid,block) for block in ref['blockIds'])
            return pairs

        for claim in draft['claims']:
            keys={'text','nature','level','refs','independence','payment','rebutsClaim'};fields(claim,keys,keys)
            require(text(claim['text']) and claim['nature'] in ('fact','author_claim','inference'))
            require(claim['level'] in ('E0','E1','E2','E3'))
            require(claim['rebutsClaim'] is None or text(claim['rebutsClaim']))
            require(claim['nature']!='inference' or claim['level']=='E0','Inferences stay E0')
            pairs=references(claim['refs'])
            validate_independence(claim,pairs,receipts)
            payment=claim['payment']
            if payment is not None:
                fields(payment,{'stage','basis','refs'},{'stage','basis','refs'})
                require(payment['stage'] in ('intent','quote','paid') and text(payment['basis']))
                require(references(payment['refs'])<=pairs,'Payment verification must cite the claim material')
            if claim['level']=='E3':require(claim['nature']=='fact' and payment is not None,'E3 requires verified payment material')
        for counter in draft['counterEvidence']:
            keys={'text','nature','level','refs','rebutsClaim'}
            fields(counter,keys,keys)
            require(text(counter['text']) and text(counter['rebutsClaim']))
            require(counter['nature'] in ('fact','author_claim','inference'))
            require(counter['level'] in ('E0','E1') and
                    (counter['nature']!='inference' or counter['level']=='E0'))
            references(counter['refs'])
        if draft['disposition']!='deferred':
            require(any(data['sourceId']==candidate['sourceId'] and candidate['url'] in (data['originalUrl'],data['finalUrl']) for data in receipts.values()),'Read the candidate itself before disposition')
        if draft['target'] is not None:
            target=value(self.records.read_record(draft['target']['recordId']))['record']
            require(target['kind'] in ('Trend','Idea') and not target['archived'] and target['mergedInto'] is None)
            require(target['revision']==draft['target']['revision'],'Update target changed; review the current version')
        self.authorize()
        keys=('sourceId','originalUrl','finalUrl','fetchedAt','precision','publishedAt','publishedDate','dateBasis','truncated')
        return dict(draft=draft,draftHash=digest(draft),bindings=[dict(receiptId=rid,**{k:data[k] for k in keys}) for rid,data in sorted(receipts.items())])


def validate_independence(claim,pairs,receipts):
    samples=claim['independence'];require(isinstance(samples,list) and len(samples)<=100)
    actors=set();origins=set();locations=set();sources=set()
    for sample in samples:
        keys={'receiptId','blockId','actorId','originId','basis','scope'};fields(sample,keys,keys)
        require(all(text(sample[k]) for k in keys))
        require((sample['receiptId'],sample['blockId']) in pairs,'Independence requires read samples')
        require(sample['scope'] in ('same_site','cross_site'))
        actors.add(sample['actorId']);origins.add(sample['originId']);locations.add(sample['blockId'].rsplit('-',1)[0])
        sources.add(urlsplit(receipts[sample['receiptId']]['finalUrl']).hostname)
    if claim['level']=='E2':
        require(len(samples)>=2 and len(actors)==len(origins)==len(locations)==len(samples),'E2 needs distinct authors and original observations')
        expected='cross_site' if len(sources)>1 else 'same_site'
        require(all(sample['scope']==expected for sample in samples),'State same-site versus cross-site independence')
