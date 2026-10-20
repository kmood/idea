import tempfile
import unittest
from pathlib import Path
from research.runner import Runner
from research.reader import Reader


class DedupeTests(unittest.TestCase):
    def ok(self,result):
        self.assertTrue(result['ok'],result);return result['value']

    def test_url_normalization_is_conservative(self):
        from research.dedupe import normalize_url,locator
        self.assertEqual(normalize_url('https://Example.com/p?a=1&utm_source=x&reply=2#comment-3'),'https://example.com/p?a=1&reply=2#comment-3')
        self.assertNotEqual(normalize_url('https://example.com/p?reply=1'),normalize_url('https://example.com/p?reply=2'))
        self.assertNotEqual(normalize_url('https://example.com/p?a=1&a=2'),normalize_url('https://example.com/p?a=2&a=1'))
        self.assertEqual(locator('S','https://example.com/old',post_id='42'),locator('S','https://example.com/new',post_id='42'))
        self.assertNotEqual(locator('S','https://example.com/p',post_id='42'),locator('S','https://example.com/p',post_id='42',reply_id='1'))

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db.sqlite3';self.time=1000;self.runner=Runner(self.path,clock=lambda:self.time)
        self.token=self.ok(self.runner.start('run','owner',[],[]))['token']
        source=dict(id='S',kind='Source',name='Forum',url='https://example.com',audience=['teachers'],languages=['en'],accessStatus='untried',lastAttempt=None,lastSuccess=None)
        self.ok(self.runner.bridge('run',self.token).register_source(source,'source'))

    def read(self,url,body):
        class Fetch:
            def fetch(self,*args,**kwargs):return dict(ok=True,value=dict(originalUrl=url,finalUrl=url,headers={'content-type':'text/plain'},body=body))
        return self.ok(Reader(self.runner.store,'run',self.token,fetcher=Fetch()).read('S',url,url))['receipt']['id']

    def test_repeated_read_new_reply_and_variant(self):
        from research.dedupe import Deduplicator
        old=self.read('https://example.com/p?utm_source=one',b'Need terminology review.')
        same=self.read('https://example.com/p?utm_source=two',b'Need terminology review.')
        dedupe=Deduplicator(self.path)
        result=self.ok(dedupe.inspect(same))
        self.assertEqual(result['matches'][0]['receiptId'],old)
        self.assertEqual(result['matches'][0]['relation'],'same_content')
        updated=self.read('https://example.com/p',b'Need terminology review.\n\nA new reply requests a glossary.')
        result=self.ok(dedupe.inspect(updated));self.assertTrue(all(m['relation']=='changed_content' for m in result['matches']))
        variant=self.read('https://example.com/other',b'Need terminology review.')
        result=self.ok(dedupe.inspect(variant));self.assertEqual(result['matches'],[])
        suggestion=self.ok(dedupe.possible_duplicate(variant,old,'Similar wording; audience may differ'))
        self.assertEqual(suggestion['status'],'possibleDuplicate')
        self.assertFalse(suggestion['merge'])

    def test_export_import_keeps_receipt_identity_and_paging(self):
        from research.dedupe import Deduplicator
        from records.exchange import Exchange
        import json
        old=self.read('https://example.com/p?utm_source=one',b'Original need')
        current=self.read('https://example.com/p?utm_source=two',b'Original need')
        output=self.path.parent/'public.json';self.ok(Exchange(self.path).export_research(output))
        imported=self.path.parent/'imported.sqlite3';self.ok(Exchange(imported).import_research(json.loads(output.read_text()),'import'))
        d=Deduplicator(imported);cursor='';found=[]
        while True:
            result=self.ok(d.inspect(current,cursor=cursor,limit=1));found+=result['matches'];cursor=result['nextCursor']
            if cursor is None:break
        self.assertEqual([m['receiptId'] for m in found],[old])

    def test_public_outcomes_and_business_links_survive_import(self):
        from research.dedupe import Deduplicator,locator
        from records.service import ResearchStore
        from records.exchange import Exchange
        import json
        receipt=self.read('https://example.com/p',b'Original need')
        store=ResearchStore(self.path);data=self.ok(store.read_record(receipt))['record']['data']
        observation=dict(receiptId=receipt,blockIds=[data['blocks'][0]['blockId']],replyIds=[],independence=[],precision='unknown',dateBasis=None,paymentVerification=None)
        evidence=dict(id='E',kind='Evidence',sourceId='S',url='https://example.com/p',claim='Need',summary='Need',publishedAt=None,accessedAt=data['fetchedAt'],nature='author_claim',level='E1',paymentSignal=None,rebutsClaim=None,observation=observation)
        self.ok(store.create_research(evidence,'evidence'))
        for key in ('I1','I2'):
            idea=dict(id=key,kind='Idea',title=key,audience='teachers',problem='Review terminology',earningHypothesis='Service',industry=['education'],sideHustleTypes=['service'],markets=['overseas'],researchStatus='待验证',evidenceIds=['E'])
            self.ok(store.create_research(idea,key))
        key=locator('S','https://example.com/p',post_id='post-42')
        outcome=dict(id='OUT',kind='ResearchArtifact',artifactType='CandidateOutcome',data=dict(runId='run',candidateId='C',sourceId='S',locator=key,status='idea',reason='Two delivery variants',nextCondition=None,recordRefs=[dict(recordId='I1',revision=1),dict(recordId='I2',revision=1)]))
        self.ok(store.create_research(outcome,'outcome'))
        output=self.path.parent/'bundle.json';self.ok(Exchange(self.path).export_research(output))
        imported=self.path.parent/'copy.sqlite3';self.ok(Exchange(imported).import_research(json.loads(output.read_text()),'import'))
        dedupe=Deduplicator(imported)
        self.assertEqual([r['recordId'] for r in self.ok(dedupe.linked_records(receipt))['items']],['E','I1','I2'])
        result=self.ok(dedupe.inspect(receipt,post_id='post-42'))
        self.assertEqual(result['outcomes'][0]['outcomeId'],'OUT')
        self.assertEqual(result['matches'],[])  # Two ideas are not two new observations.

    def test_new_run_finds_old_receipt(self):
        from research.dedupe import Deduplicator
        old=self.read('https://example.com/p?utm_source=one',b'Original need')
        self.time+=91
        token=self.ok(self.runner.start('next-run','new-owner',[],[]))['token']
        class Fetch:
            def fetch(self,*args,**kwargs):return dict(ok=True,value=dict(originalUrl='https://example.com/p',finalUrl='https://example.com/p',headers={'content-type':'text/plain'},body=b'Original need'))
        receipt=self.ok(Reader(self.runner.store,'next-run',token,fetcher=Fetch()).read('S','https://example.com/p','next'))['receipt']['id']
        self.assertEqual(self.ok(Deduplicator(self.path).inspect(receipt))['matches'][0]['receiptId'],old)
