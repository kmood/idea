import copy
import tempfile
import unittest
from pathlib import Path
from research.runner import Runner
from research.reader import Reader


class AnalysisTests(unittest.TestCase):
    def ok(self,result):
        self.assertTrue(result['ok'],result);return result['value']

    def setUp(self):
        from research.analysis import Analyzer
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db.sqlite3';self.runner=Runner(self.path)
        self.token=self.ok(self.runner.start('run','owner',[],[]))['token'];bridge=self.runner.bridge('run',self.token)
        source=dict(id='S',kind='Source',name='Forum',url='https://example.com',audience=['teachers'],languages=['en'],accessStatus='untried',lastAttempt=None,lastSuccess=None)
        self.ok(bridge.register_source(source,'source'))
        self.ok(bridge.request('search','education',tool='synthetic'))
        result=dict(status='completed',reason=None,discoveries=[dict(sourceId='S',url='https://example.com/thread',title='Terminology',snippet='Not evidence')])
        self.candidate=self.ok(bridge.submit('search',result))['candidateIds'][0]
        class Fetch:
            def fetch(self,*args,**kwargs):
                return dict(ok=True,value=dict(originalUrl='https://example.com/thread',finalUrl='https://example.com/thread',headers={'content-type':'text/plain'},body=b'Teacher A needs terminology checks.\n\nTeacher B needs the same help.'))
        reader=Reader(self.runner.store,'run',self.token,fetcher=Fetch())
        receipt=self.ok(reader.read('S','https://example.com/thread',self.candidate))['receipt']
        self.ref=dict(receiptId=receipt['id'],blockIds=[receipt['data']['blocks'][0]['blockId']])
        self.second=receipt['data']['blocks'][1]['blockId']
        self.draft=dict(candidateId=self.candidate,disposition='idea',reason='Concrete need with a service hypothesis',nextCondition=None,
            claims=[dict(text='A teacher requests terminology checks',nature='author_claim',level='E1',refs=[self.ref],independence=[],payment=None,rebutsClaim=None)],
            unknowns=['Willingness to pay','Cost'],counterEvidence=[],target=None,
            content=dict(title='Terminology review service',audience='teachers',problem='Inconsistent terminology',earningHypothesis='Charge for review; hypothesis',industry=['education'],sideHustleTypes=['service'],markets=['overseas'],cost=None))
        self.analyzer=Analyzer(self.runner.store,'run',self.token)

    def test_idea_unknown_cost_and_receipt_bound_dates(self):
        result=self.ok(self.analyzer.validate(self.draft))
        self.assertIsNone(result['draft']['content']['cost'])
        self.assertEqual(result['bindings'][0]['sourceId'],'S')
        self.assertEqual(result['bindings'][0]['precision'],'unknown')
        self.assertNotIn('Teacher B',str(result))

    def test_fake_blocks_receipts_and_cache_loss_fail(self):
        for ref in (dict(self.ref,receiptId='made-up'),dict(self.ref,blockIds=['unread-reply'])):
            draft=copy.deepcopy(self.draft);draft['claims'][0]['refs']=[ref]
            self.assertFalse(self.analyzer.validate(draft)['ok'])
        for path in (self.path.parent/'research-cache').glob('*.json'):path.unlink()
        self.assertFalse(self.analyzer.validate(self.draft)['ok'])

    def test_inference_cannot_be_upgraded_and_payment_needs_verification(self):
        draft=copy.deepcopy(self.draft);claim=draft['claims'][0]
        claim.update(nature='inference',level='E1');self.assertFalse(self.analyzer.validate(draft)['ok'])
        claim.update(nature='author_claim',level='E3',payment=dict(stage='paid',basis='Author says so',refs=[self.ref]))
        self.assertFalse(self.analyzer.validate(draft)['ok'])
        claim.update(nature='fact',payment=None);self.assertFalse(self.analyzer.validate(draft)['ok'])
        claim['payment']=dict(stage='quote',basis='Visible purchase request; manual verification basis',refs=[self.ref])
        self.ok(self.analyzer.validate(draft))

    def test_e2_requires_independent_read_samples(self):
        draft=copy.deepcopy(self.draft);claim=draft['claims'][0];claim['level']='E2'
        self.assertFalse(self.analyzer.validate(draft)['ok'])
        claim['refs'][0]['blockIds'].append(self.second)
        sample=dict(receiptId=self.ref['receiptId'],blockId=self.ref['blockIds'][0],actorId='teacher-a',originId='post-a',basis='Distinct original author',scope='same_site')
        claim['independence']=[sample,dict(sample,blockId=self.second,originId='post-b')]
        self.assertFalse(self.analyzer.validate(draft)['ok'])
        claim['independence'][1]['actorId']='teacher-b';self.ok(self.analyzer.validate(draft))
        claim['independence'][1]['blockId']='unread-comment';self.assertFalse(self.analyzer.validate(draft)['ok'])

    def test_trend_deferred_and_rejected_rules(self):
        draft=copy.deepcopy(self.draft);draft.update(disposition='trend',content=dict(title='Terminology gap',summary='Observed repeated work',impact=dict(nature='inference',text='AI output needs checking'),questions=['Who pays?']))
        self.ok(self.analyzer.validate(draft))
        draft.update(disposition='deferred',claims=[],content=None,nextCondition='Read the original discussion')
        self.ok(self.analyzer.validate(draft))
        draft['nextCondition']=None;self.assertFalse(self.analyzer.validate(draft)['ok'])
        draft.update(disposition='rejected',nextCondition='Recheck if more detail appears')
        self.assertFalse(self.analyzer.validate(draft)['ok'])
        draft['claims']=self.draft['claims'];self.ok(self.analyzer.validate(draft))

    def test_no_personal_fields_or_unreferenced_counterclaims(self):
        draft=copy.deepcopy(self.draft);draft['favorite']=True
        self.assertFalse(self.analyzer.validate(draft)['ok'])
        draft=copy.deepcopy(self.draft);draft['counterEvidence']=[dict(text='Opposite',refs=[dict(self.ref,blockIds=['not-read'])])]
        self.assertFalse(self.analyzer.validate(draft)['ok'])
        self.ok(self.runner.store.execution.cancel('run',self.token))
        self.assertFalse(self.analyzer.validate(self.draft)['ok'])

    def test_update_requires_current_existing_business_record(self):
        from records.service import ResearchStore
        store=ResearchStore(self.path)
        record=dict(id='T',kind='Trend',title='Existing trend',summary='Original observation',impact=dict(nature='inference',text='Unknown'),questions=['Who pays?'],evidenceIds=['E'])
        evidence=dict(id='E',kind='Evidence',sourceId='S',url='https://example.com/thread',claim='Observed need',summary='Observed need',publishedAt=None,accessedAt='2026-10-20T00:00:00Z',nature='author_claim',level='E1',paymentSignal=None,rebutsClaim=None)
        self.ok(store.create_research(evidence,'evidence'))
        self.ok(store.create_research(record,'trend'))
        draft=copy.deepcopy(self.draft);draft.update(disposition='update',target=dict(recordId='T',revision=1),content=dict(summary='New contrary observation'))
        self.ok(self.analyzer.validate(draft))
        self.ok(store.patch_research('T',1,dict(summary='Other edit'),'Reviewed','edit'))
        self.assertFalse(self.analyzer.validate(draft)['ok'])
        draft['target']=dict(recordId='S',revision=1)
        self.assertFalse(self.analyzer.validate(draft)['ok'])

    def test_e2_duplicate_text_across_receipts_is_not_independent(self):
        draft=copy.deepcopy(self.draft);claim=draft['claims'][0];claim['level']='E2'
        # A second URL repeats the very same text, with claimed different identities.
        class Fetch:
            def fetch(self,*args,**kwargs):
                return dict(ok=True,value=dict(originalUrl='https://example.com/repost',finalUrl='https://example.com/repost',headers={'content-type':'text/plain'},body=b'Teacher A needs terminology checks.'))
        reader=Reader(self.runner.store,'run',self.token,fetcher=Fetch())
        receipt=self.ok(reader.read('S','https://example.com/repost','repost'))['receipt']
        second=dict(receiptId=receipt['id'],blockIds=[receipt['data']['blocks'][0]['blockId']])
        claim['refs'].append(second)
        claim['independence']=[dict(receiptId=ref['receiptId'],blockId=ref['blockIds'][0],actorId=f'person-{n}',originId=f'post-{n}',basis='Claimed distinct original',scope='same_site') for n,ref in enumerate(claim['refs'])]
        self.assertFalse(self.analyzer.validate(draft)['ok'])
