import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from research.runner import Runner


class ResearchAdversarialTests(unittest.TestCase):
    def ok(self,result):
        self.assertTrue(result['ok'],result);return result['value']

    def test_competing_resumes_have_one_owner_and_stale_token_cannot_cancel(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'research.sqlite3';clock=[1000]
        original=Runner(path,clock=lambda:clock[0])
        stale=self.ok(original.start('run','initial',[],[]))['token'];clock[0]+=91
        barrier=threading.Barrier(2)
        def acquire(owner):
            runner=Runner(path,clock=lambda:clock[0]);barrier.wait()
            return runner.resume('run',owner)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(acquire,('owner-a','owner-b')))
        self.assertEqual(sum(result['ok'] for result in results),1)
        self.assertEqual([result['error']['code'] for result in results if not result['ok']],['BUSY'])
        rejected=original.store.execution.cancel('run',stale)
        self.assertEqual(rejected['error']['code'],'LEASE_EXPIRED')


if __name__=='__main__':unittest.main()
