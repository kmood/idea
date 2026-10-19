import tempfile
import unittest
from pathlib import Path
from records.runtime import ResearchRuntimeStore


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'records.sqlite3'
        self.time = 1000.0
        self.store = ResearchRuntimeStore(self.path, clock=lambda:self.time)
        self.request = dict(sourceIds=[],queries=['query'],limits=dict(searches=1,candidates=1,auxiliary=1,total=3),deadline='1970-01-01T00:30:00Z')
        self.value(self.store.begin('run',self.request))

    def value(self, result):
        self.assertTrue(result['ok'], result)
        return result['value']

    def test_lease_contention_expiry_and_stale_write(self):
        token = self.value(self.store.execution.acquire('run','one'))
        other = ResearchRuntimeStore(self.path,clock=lambda:self.time)
        self.assertEqual(other.execution.acquire('run','two')['error']['code'],'BUSY')
        self.time += 91
        replacement = self.value(other.execution.acquire('run','two'))
        self.assertGreater(replacement['fence'],token['fence'])
        intent = dict(recordId='future',operationId='create',requestHash='a'*64,expectedRevision=None)
        self.assertFalse(self.store.save_intent('run','step',intent,token=token)['ok'])
        self.value(other.save_intent('run','step',intent,token=replacement))
        self.assertFalse(self.store.save_intent('run','step',intent,token=token)['ok'])

    def test_reserved_lost_result_consumes_budget_and_replays_once(self):
        token = self.value(self.store.execution.acquire('run','one'))
        grant = self.value(self.store.execution.reserve('run',token,'search1','search'))
        self.assertEqual(self.value(self.store.execution.reserve('run',token,'search1','search')),grant)
        self.assertEqual(self.store.execution.reserve('run',token,'search2','search')['error']['code'],'BUDGET_EXHAUSTED')
        self.assertEqual(self.store.execution.reserve('run',token,'search1','request')['error']['code'],'IDEMPOTENCY_CONFLICT')
        self.time += 31
        self.assertFalse(self.store.execution.finish('run',token,'search1','a'*64)['ok'])
        self.assertEqual(self.store.execution.reserve('run',token,'search2','search')['error']['code'],'BUDGET_EXHAUSTED')

    def test_restart_deadline_and_explicit_extension_are_idempotent(self):
        token = self.value(self.store.execution.acquire('run','one'))
        self.value(self.store.execution.reserve('run',token,'s1','search'))
        self.value(self.store.execution.extend('run',token,'approval1',dict(searches=1,candidates=0,auxiliary=0,total=1),'1970-01-01T00:35:00Z'))
        self.value(self.store.execution.extend('run',token,'approval1',dict(searches=1,candidates=0,auxiliary=0,total=1),'1970-01-01T00:35:00Z'))
        reopened = ResearchRuntimeStore(self.path,clock=lambda:self.time)
        self.value(reopened.execution.reserve('run',token,'s2','search'))
        self.assertFalse(reopened.execution.reserve('run',token,'s3','search')['ok'])
        self.time = 2101
        token = self.value(reopened.execution.acquire('run','one'))
        self.assertEqual(reopened.execution.reserve('run',token,'r1','request')['error']['code'],'DEADLINE_EXCEEDED')

    def test_repeated_candidate_counts_once_but_all_requests_count(self):
        token = self.value(self.store.execution.acquire('run','one'))
        self.value(self.store.execution.reserve('run',token,'body1','discussion','thread1'))
        self.value(self.store.execution.reserve('run',token,'body2','discussion','thread1'))
        self.assertFalse(self.store.execution.reserve('run',token,'body3','discussion','thread2')['ok'])
        self.value(self.store.execution.reserve('run',token,'robots','request'))
        self.assertEqual(self.store.execution.reserve('run',token,'redirect','request')['error']['code'],'BUDGET_EXHAUSTED')

    def test_cancel_and_foreign_database_credentials_fail(self):
        token = self.value(self.store.execution.acquire('run','one'))
        self.assertFalse(self.store.execution.reserve('run',token | {'dbInstanceId':'foreign'},'s1','search')['ok'])
        self.value(self.store.execution.cancel('run',token))
        self.assertEqual(self.store.execution.reserve('run',token,'s1','search')['error']['code'],'CANCELLED')

    def test_restore_invalidates_pre_backup_credentials_and_keeps_budget(self):
        from records.backup import backup_local, restore_local
        token = self.value(self.store.execution.acquire('run','one'))
        self.value(self.store.execution.reserve('run',token,'s1','search'))
        backup = self.path.parent / 'backup.sqlite3'; restored = self.path.parent / 'restore.sqlite3'
        self.value(backup_local(self.path,backup)); self.value(restore_local(backup,restored))
        other = ResearchRuntimeStore(restored,clock=lambda:self.time)
        self.assertFalse(other.execution.reserve('run',token,'r1','request')['ok'])
        new = self.value(other.execution.acquire('run','one'))
        self.assertNotEqual(new['dbInstanceId'],token['dbInstanceId'])
        self.assertGreater(new['fence'],token['fence'])
        self.assertEqual(other.execution.reserve('run',new,'s2','search')['error']['code'],'BUDGET_EXHAUSTED')

    def test_completed_result_replays_without_refunding_a_call(self):
        token = self.value(self.store.execution.acquire('run','one'))
        self.value(self.store.execution.reserve('run',token,'s1','search'))
        completed = self.value(self.store.execution.finish('run',token,'s1','a'*64))
        self.assertEqual(self.value(self.store.execution.finish('run',token,'s1','a'*64)),completed)
        self.assertFalse(self.store.execution.finish('run',token,'s1','b'*64)['ok'])
        self.assertFalse(self.store.execution.reserve('run',token,'s2','search')['ok'])

    def test_concurrent_connections_have_exactly_one_owner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier = Barrier(2)
        other = ResearchRuntimeStore(self.path,clock=lambda:self.time)
        def acquire(pair):
            store, owner = pair
            barrier.wait(timeout=5)
            return store.execution.acquire('run',owner)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(acquire, [(self.store,'one'),(other,'two')]))
        self.assertEqual(sum(result['ok'] for result in results),1)
        self.assertEqual([r['error']['code'] for r in results if not r['ok']],['BUSY'])

    def test_execution_ledger_corruption_prevents_backup(self):
        import json
        from contextlib import closing
        from records.backup import backup_local
        token = self.value(self.store.execution.acquire('run','one'))
        self.value(self.store.execution.reserve('run',token,'s1','search'))
        with closing(self.store.db.connect()) as conn:
            ledger = json.loads(conn.execute('SELECT payload FROM research_execution').fetchone()[0])
            ledger['calls']['s2'] = dict(ledger['calls']['s1'],callId='s2')
            conn.execute('UPDATE research_execution SET payload=?',(json.dumps(ledger),))
        target = self.path.parent / 'invalid.sqlite3'
        self.assertFalse(backup_local(self.path,target)['ok'])
        self.assertFalse(target.exists())
