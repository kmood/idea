import tempfile
import unittest
from pathlib import Path


class RunnerFacadeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'records.sqlite3'
        self.time = 1000.0

    def value(self,result):
        self.assertTrue(result['ok'],result)
        return result['value']

    def test_runner_defaults_resume_and_reports_remaining_budget(self):
        from research.runner import Runner
        runner = Runner(self.path,clock=lambda:self.time)
        started = self.value(runner.start('run2','runner',[],['query']))
        self.assertEqual(started['state']['limits']['total'],40)
        self.assertEqual(started['state']['deadline'],self.time+1200)
        token = started['token']
        self.value(runner.store.execution.reserve('run2',token,'search','search'))
        self.time += 10
        retried = self.value(runner.start('run2','runner',[],['query']))
        self.assertEqual(retried['state']['deadline'],started['state']['deadline'])
        self.assertFalse(runner.start('run2','runner',[],['changed'])['ok'])
        resumed = self.value(runner.resume('run2','runner'))
        self.assertEqual(resumed['state']['used']['searches'],1)
        self.assertEqual(resumed['state']['remaining']['total'],39)
        self.time += 1201
        ended = self.value(runner.resume('run2','runner'))
        self.assertEqual(ended['status'],'partial')
        self.assertEqual(ended['reason'],'deadline')
