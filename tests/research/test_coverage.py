import copy
import json
import tempfile
import unittest
from pathlib import Path

from records.service import ResearchStore
from research.reader import Reader
from research.runner import Runner


class CoverageTests(unittest.TestCase):
    def ok(self,result):
        self.assertTrue(result['ok'],result);return result['value']

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db.sqlite3';self.time=1000
        self.runner=Runner(self.path,clock=lambda:self.time)
        productive=self.ok(self.runner.start('productive','collector',['S'],[]))
        source=dict(id='S',kind='Source',name='Builder forum',url='https://example.com',
                    audience=['small businesses'],languages=['en'],accessStatus='untried',
                    lastAttempt=None,lastSuccess=None,profile=dict(domain='example.com',
                    subentries=['https://example.com/forum'],industries=['education'],
                    sourceType='community',accessBoundary='public threads',
                    recheckReason='sample non-commerce demand'))
        self.store=ResearchStore(self.path);self.ok(self.store.create_research(source,'source'))
        class Fetch:
            def fetch(self,*args,**kwargs):
                return dict(ok=True,value=dict(originalUrl='https://example.com/thread',
                    finalUrl='https://example.com/thread',headers={'content-type':'text/plain'},
                    body=b'A small education business asks for an AI-assisted workflow review.'))
        receipt=self.ok(Reader(self.runner.store,'productive',productive['token'],fetcher=Fetch()).read(
            'S','https://example.com/thread','candidate'))['receipt']
        evidence=dict(id='E',kind='Evidence',sourceId='S',url='https://example.com/thread',
                      claim='A small education business asks for workflow review',
                      summary='Observed workflow review request',publishedAt=None,
                      accessedAt=receipt['data']['fetchedAt'],nature='author_claim',level='E1',
                      paymentSignal=None,rebutsClaim=None,observation=dict(receiptId=receipt['id'],
                      blockIds=[receipt['data']['blocks'][0]['blockId']],replyIds=[],independence=[],
                      precision='unknown',dateBasis=None,paymentVerification=None))
        self.evidence=self.ok(self.store.create_research(evidence,'evidence'))
        for run_id in ('empty-1','empty-2','empty-3'):
            self.ok(self.runner.store.begin(run_id,dict(sourceIds=['S'],queries=[],
                limits=dict(searches=12,candidates=10,auxiliary=8,total=40),
                deadline='2030-01-01T00:00:00+00:00')))
        self.time=1091
        token=self.ok(self.runner.store.execution.acquire('empty-3','reviewer'))
        self.coverage=self.runner.coverage('empty-3',token)
        self.draft=dict(runIds=['productive'],sourceRefs=[dict(recordId='S',revision=1)],
            evidenceRefs=[dict(recordId='E',revision=1)],gaps=['domestic professional services'],
            qualityReasons=['One public community is readable; payment remains unknown'],
            recommendation='concentrate',reason='Broaden beyond one English community',
            coverage=dict(industries=['education'],audiences=['small businesses'],markets=['overseas'],
                sideHustleTypes=['service'],sourceTypes=['community'],readScopes=['plain text'],
                sustainableSources=['S'],
                alternatives=['Add a domestic public community'],
                duplicateHandling='Stable receipt and candidate identities are retained',
                patrolPlan='Revisit with bounded overlap in later authorized runs',
                channelAdjustment=None))

    def test_grounded_review_publishes_structured_dimensions_and_replays(self):
        from records.exchange import Exchange
        first=self.ok(self.coverage.publish(self.draft))
        self.assertEqual(first['record']['artifactType'],'CoverageReview')
        self.assertEqual(first['record']['data']['coverage']['industries'],['education'])
        self.assertEqual(first['record']['data']['coverage']['noNewEvidenceRuns'],[])
        self.assertEqual(self.ok(self.coverage.publish(self.draft)),first)
        self.assertEqual(len(self.ok(self.store.list_history(first['record']['id']))['items']),1)
        bundle=self.path.parent/'coverage.json';self.ok(Exchange(self.path).export_research(bundle))
        imported=Exchange(self.path.parent/'imported.sqlite3')
        self.ok(imported.import_research(json.loads(bundle.read_text()),'coverage-import'))
        restored=self.ok(ResearchStore(imported.db.path).read_record(first['record']['id']))['record']
        self.assertEqual(restored,first['record'])

    def test_references_must_exist_and_evidence_must_belong_to_reviewed_runs(self):
        missing=copy.deepcopy(self.draft);missing['sourceRefs'][0]['recordId']='missing'
        self.assertEqual(self.coverage.publish(missing)['error']['code'],'NOT_FOUND')
        wrong=copy.deepcopy(self.draft);wrong['runIds']=['empty-1']
        self.assertEqual(self.coverage.publish(wrong)['error']['code'],'VALIDATION_ERROR')
        invented=copy.deepcopy(self.draft);invented['coverage']['sourceTypes']=['report']
        self.assertEqual(self.coverage.publish(invented)['error']['code'],'VALIDATION_ERROR')
        valid=self.ok(self.coverage.publish(self.draft))['record']
        bad_data=copy.deepcopy(valid['data']);bad_data['coverage']['sourceTypes']=['report']
        bad=dict(id='coverage:invented',kind='ResearchArtifact',artifactType='CoverageReview',data=bad_data)
        self.assertEqual(self.store.create_research(bad,'invented')['error']['code'],'VALIDATION_ERROR')

    def test_three_trailing_empty_runs_require_channel_adjustment(self):
        draft=copy.deepcopy(self.draft)
        draft['runIds']=['productive','empty-1','empty-2','empty-3']
        draft['recommendation']='concentrate'
        self.assertEqual(self.coverage.publish(draft)['error']['code'],'VALIDATION_ERROR')
        draft['recommendation']='adjust'
        draft['coverage']['channelAdjustment']='Replace repeated broad queries with domestic professional forums'
        result=self.ok(self.coverage.publish(draft))
        self.assertEqual(result['record']['data']['coverage']['noNewEvidenceRuns'],
                         ['empty-1','empty-2','empty-3'])

    def test_incremental_requires_readiness_reasons_not_counts_or_one_empty_round(self):
        weak=copy.deepcopy(self.draft);weak['runIds']=['empty-1'];weak['evidenceRefs']=[]
        weak['recommendation']='incremental';weak['coverage']['sustainableSources']=[]
        self.assertEqual(self.coverage.publish(weak)['error']['code'],'VALIDATION_ERROR')
        ready=copy.deepcopy(self.draft);ready['recommendation']='incremental'
        result=self.ok(self.coverage.publish(ready))
        self.assertEqual(result['recommendation'],'incremental')
        self.assertEqual(self.ok(self.runner.store.inspect_run('empty-3'))['run']['status'],'pending')
        self.assertFalse(self.store.list_records('Assessment')['value']['items'])


if __name__=='__main__':unittest.main()
