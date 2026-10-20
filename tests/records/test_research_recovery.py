import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from records.backup import backup_local,restore_local
from records.exchange import Exchange
from records.identity import IdentityStore
from records.migrations import inspect_recovery
from records.network_policy import NetworkPolicyStore
from records.personal import PersonalStore
from records.service import ResearchStore
from research.analysis import Analyzer
from research.reader import Reader
from research.runner import Runner


class ResearchRecoveryTests(unittest.TestCase):
    def ok(self,result):
        self.assertTrue(result['ok'],result);return result['value']

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'db.sqlite3';self.time=1000
        self.runner=Runner(self.path,clock=lambda:self.time);self.store=ResearchStore(self.path)
        source=dict(id='S',kind='Source',name='Forum',url='https://example.com',
                    audience=['builders'],languages=['en'],accessStatus='untried',
                    lastAttempt=None,lastSuccess=None)
        self.ok(self.store.create_research(source,'source'))
        started=self.ok(self.runner.start('run','owner',['S'],[]));self.token=started['token']
        self.ok(NetworkPolicyStore(self.runner.store).remember(
            'https://example.com','S','run',self.token,404,'',3,60))
        bridge=self.runner.bridge('run',self.token)
        self.ok(bridge.request('search','workflow request',tool='synthetic'))
        result=dict(status='completed',reason=None,discoveries=[dict(sourceId='S',
            url='https://example.com/thread',title='Workflow request',snippet='Discovery only')])
        self.candidate=self.ok(bridge.submit('search',result))['candidateIds'][0]

        class Fetch:
            def fetch(self,*args,**kwargs):
                return dict(ok=True,value=dict(originalUrl='https://example.com/thread',
                    finalUrl='https://example.com/thread',headers={'content-type':'text/plain'},
                    body=b'A builder requests an AI-assisted workflow review.'))
        self.fetch=Fetch();reader=Reader(self.runner.store,'run',self.token,fetcher=self.fetch)
        self.receipt=self.ok(reader.read('S','https://example.com/thread',self.candidate))['receipt']
        block=self.receipt['data']['blocks'][0]['blockId']
        draft=dict(candidateId=self.candidate,disposition='idea',reason='Visible specific request',
            nextCondition=None,unknowns=['payment'],counterEvidence=[],target=None,
            claims=[dict(text='A builder requests an AI-assisted workflow review',nature='author_claim',
                level='E1',refs=[dict(receiptId=self.receipt['id'],blockIds=[block])],
                independence=[],payment=None,rebutsClaim=None)],
            content=dict(title='Workflow review',audience='builders',problem='Workflow friction',
                earningHypothesis='Charge for review; hypothesis',industry=['professional services'],
                sideHustleTypes=['service'],markets=['overseas'],cost=None))
        validated=self.ok(Analyzer(self.runner.store,'run',self.token).validate(draft))
        publication=self.runner.publication('run',self.token)
        self.manifest=self.ok(publication.prepare(validated,'thread:workflow'))['manifest']
        self.partial=self.ok(publication.resume(self.manifest['id'],max_steps=1))

        progress=self.runner.progress('run',self.token)
        self.ok(progress.discover('S','ordered',[self.candidate],'cursor-1','overlap one'))
        outcome=dict(id='outcome:checkpoint',kind='ResearchArtifact',artifactType='CandidateOutcome',
            data=dict(runId='run',candidateId=self.candidate,sourceId='S',locator='thread:workflow',
                      status='unchanged',reason='Explicitly reviewed',nextCondition=None,recordRefs=[]))
        self.ok(self.store.create_research(outcome,'checkpoint-outcome'))
        self.ok(progress.settle('S',self.candidate,outcome['id']))
        personal=PersonalStore(self.path)
        first=self.ok(personal.set_personal_state('S',None,{'favorite':True,'notes':'PRIVATE'},'p1'))
        self.ok(personal.set_personal_state('S',first['revision'],{'validationStage':'准备验证'},'p2'))

    def test_local_backup_restores_all_runtime_private_history_and_requires_reread(self):
        original=self.ok(inspect_recovery(self.path))
        self.assertEqual(original['mode'],'local-backup')
        self.assertEqual(original['receipts'][0]['cacheStatus'],'available')
        backup=self.root/'backup.sqlite3';restored_dir=self.root/'restored';restored_dir.mkdir()
        restored=restored_dir/'db.sqlite3'
        summary=self.ok(backup_local(self.path,backup));self.ok(restore_local(backup,restored))
        for table in ('research_runs','research_intents','research_execution','research_network',
                      'research_searches','research_candidates','research_readings',
                      'research_publications','research_progress','personal_events'):
            self.assertGreater(summary['counts'][table],0)
        recovered=self.ok(inspect_recovery(restored))
        self.assertEqual(recovered['mode'],'local-backup')
        self.assertTrue(recovered['manifests'][0]['localPlan'])
        self.assertEqual(recovered['manifests'][0]['nextAction'],'resume_local_plan')
        self.assertEqual(recovered['receipts'][0]['nextAction'],'reread')
        self.assertEqual(recovered['localOnly']['privateStateCount'],1)
        self.assertEqual(len(self.ok(PersonalStore(restored).list_history('S'))['items']),2)
        stale=Runner(restored,clock=lambda:self.time).publication('run',self.token).resume(self.manifest['id'])
        self.assertEqual(stale['error']['code'],'LEASE_EXPIRED')
        runner=Runner(restored,clock=lambda:self.time);token=self.ok(runner.resume('run','new-owner'))['token']
        reread=self.ok(Reader(runner.store,'run',token,fetcher=self.fetch).read(
            'S','https://example.com/thread',self.candidate))['receipt']
        self.assertEqual(reread['id'],self.receipt['id'])
        self.assertEqual(len(self.ok(ResearchStore(restored).list_history(reread['id']))['items']),1)
        self.assertEqual(self.ok(runner.publication('run',token).resume(self.manifest['id']))['status'],'complete')

    def test_public_only_import_recovers_public_identity_without_private_or_local_claims(self):
        bundle_path=self.root/'public.json';self.ok(Exchange(self.path).export_research(bundle_path))
        replica_dir=self.root/'replica';replica_dir.mkdir();replica=replica_dir/'db.sqlite3'
        self.ok(Exchange(replica).import_research(json.loads(bundle_path.read_text()),'import'))
        recovered=self.ok(inspect_recovery(replica))
        self.assertEqual(recovered['mode'],'public-only')
        self.assertEqual(recovered['localOnly'],dict(runCount=0,publicationPlanCount=0,
                                                     pendingIntentCount=0,privateStateCount=0))
        manifest=recovered['manifests'][0]
        self.assertFalse(manifest['localPlan'])
        self.assertEqual(manifest['nextAction'],'reread_and_reanalyze')
        self.assertEqual(manifest['completedTargets'],[self.partial['manifest']['data']['steps'][0]['targetId']])
        self.assertTrue(manifest['pendingTargets'])
        self.assertEqual(recovered['receipts'][0]['cacheStatus'],'missing')
        self.assertEqual(recovered['checkpoints'][0]['completed'],self.candidate)
        self.assertIsNone(self.ok(PersonalStore(replica).read_record('S'))['revision'])
        latest=self.ok(IdentityStore(replica).latest_manifest('S',self.candidate))
        self.assertEqual(latest['recordId'],self.manifest['id'])
        with closing(sqlite3.connect(replica)) as conn:
            tables={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertFalse({'research_candidates','research_readings','research_progress'} & tables)


if __name__=='__main__':unittest.main()
