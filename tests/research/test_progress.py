import tempfile
import unittest
from pathlib import Path

from records.service import ResearchStore
from research.runner import Runner


class ProgressTests(unittest.TestCase):
    def ok(self,result):
        self.assertTrue(result['ok'],result)
        return result['value']

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db.sqlite3';self.time=1000
        self.runner=Runner(self.path,clock=lambda:self.time)
        self.token=self.ok(self.runner.start('run','owner',['S'],[]))['token']
        self.store=ResearchStore(self.path)
        source=dict(id='S',kind='Source',name='Forum',url='https://example.com',
                    audience=['builders'],languages=['en'],accessStatus='untried',
                    lastAttempt=None,lastSuccess=None)
        self.ok(self.store.create_research(source,'source'))
        self.progress=self.runner.progress('run',self.token)

    def outcome(self,position,status='unchanged'):
        record=dict(id='outcome:'+position,kind='ResearchArtifact',artifactType='CandidateOutcome',
                    data=dict(runId='run',candidateId=position,sourceId='S',locator='thread:'+position,
                              status=status,reason='Reviewed visible material',nextCondition=None,
                              recordRefs=[]))
        return self.ok(self.store.create_research(record,'outcome:'+position))

    def test_ordered_progress_keeps_earlier_gap_until_it_is_settled(self):
        discovered=self.ok(self.progress.discover('S','ordered',['p1','p2','p3'],'cursor-3',
                                                   'revisit the last two positions'))
        self.assertEqual(discovered['state']['discovered'],'cursor-3')
        self.ok(self.progress.begin_attempt('S','p1'))
        failed=self.ok(self.progress.fail('S','p1','network',retryable=True))
        self.assertTrue(failed['retryAllowed'])
        self.outcome('p2');later=self.ok(self.progress.settle('S','p2','outcome:p2'))
        self.assertIsNone(later['checkpoint']['data']['completed'])
        self.assertEqual(later['checkpoint']['data']['gaps'],['p1'])
        self.outcome('p3');still_gap=self.ok(self.progress.settle('S','p3','outcome:p3'))
        self.assertIsNone(still_gap['checkpoint']['data']['completed'])
        self.assertEqual(still_gap['checkpoint']['data']['processed'],['p2','p3'])
        self.outcome('p1');complete=self.ok(self.progress.settle('S','p1','outcome:p1'))
        self.assertEqual(complete['checkpoint']['data']['completed'],'p3')
        self.assertEqual(complete['checkpoint']['data']['gaps'],[])

    def test_unordered_source_uses_processed_set_without_completion_cursor(self):
        self.ok(self.progress.discover('S','unordered',['a','b'],'opaque-page',
                                       'revisit recent identities'))
        self.outcome('b');result=self.ok(self.progress.settle('S','b','outcome:b'))
        self.assertIsNone(result['checkpoint']['data']['completed'])
        self.assertEqual(result['checkpoint']['data']['processed'],['b'])
        self.outcome('a');result=self.ok(self.progress.settle('S','a','outcome:a'))
        self.assertIsNone(result['checkpoint']['data']['completed'])
        self.assertEqual(result['checkpoint']['data']['processed'],['a','b'])

    def test_overlap_and_invalid_cursor_preserve_confirmed_progress(self):
        self.ok(self.progress.discover('S','ordered',['p1','p2'],'cursor-2','overlap two'))
        for position in ('p1','p2'):
            self.outcome(position);self.ok(self.progress.settle('S',position,'outcome:'+position))
        invalid=self.ok(self.progress.discover('S','ordered',['p2','p3'],'expired-cursor',
                                                'overlap two',cursor_valid=False))
        self.assertEqual(invalid['action'],'restart_with_overlap')
        self.assertEqual(invalid['state']['positions'],['p1','p2','p3'])
        self.assertEqual(invalid['state']['discovered'],'cursor-2')
        checkpoint=self.ok(self.store.read_record('checkpoint:run:S'))['record']
        self.assertEqual(checkpoint['data']['completed'],'p2')
        self.assertEqual(len(self.ok(self.store.list_history(checkpoint['id']))['items']),3)
        recovered=self.ok(self.progress.discover('S','ordered',['p2','p3'],'cursor-2',
                                                  'overlap two',cursor_valid=True))
        self.assertFalse(recovered['state']['cursorInvalid'])
        from records.backup import backup_local
        self.ok(backup_local(self.path,self.path.parent/'cursor-recovered.sqlite3'))

    def test_one_retry_and_rate_limit_wait_are_bounded(self):
        self.ok(self.progress.discover('S','ordered',['p1','p2'],'cursor-2','overlap two'))
        first=self.ok(self.progress.begin_attempt('S','p1'))
        self.assertEqual(first['attempt'],1)
        self.ok(self.progress.fail('S','p1','timeout',retryable=True))
        second=self.ok(self.progress.begin_attempt('S','p1'))
        self.assertEqual(second['attempt'],2)
        self.ok(self.progress.fail('S','p1','timeout',retryable=True))
        self.assertEqual(self.progress.begin_attempt('S','p1')['error']['code'],'RETRY_EXHAUSTED')

        self.ok(self.progress.begin_attempt('S','p2'))
        limited=self.ok(self.progress.fail('S','p2','rate_limit',retryable=True,retry_at=1100))
        self.assertFalse(limited['retryAllowed'])
        waiting=self.progress.begin_attempt('S','p2')
        self.assertEqual(waiting['error']['code'],'RATE_LIMIT')
        self.time=1100
        self.token=self.ok(self.runner.store.execution.acquire('run','owner'))
        self.progress=self.runner.progress('run',self.token)
        self.assertEqual(self.ok(self.progress.begin_attempt('S','p2'))['attempt'],2)
        self.assertEqual(self.ok(self.runner.store.execution.inspect('run'))['used']['total'],0)

    def test_settlement_requires_matching_persisted_outcome(self):
        self.ok(self.progress.discover('S','ordered',['p1'],'cursor-1','overlap one'))
        checkpoint=self.ok(self.store.read_record('checkpoint:run:S'))['record']
        missing=self.progress.settle('S','p1','outcome:p1')
        self.assertEqual(missing['error']['code'],'NOT_FOUND')
        self.outcome('other')
        wrong=self.progress.settle('S','p1','outcome:other')
        self.assertEqual(wrong['error']['code'],'VALIDATION_ERROR')
        current=self.ok(self.store.read_record(checkpoint['id']))['record']
        self.assertEqual(current['revision'],checkpoint['revision'])

    def test_backup_restores_gap_and_single_remaining_retry(self):
        from records.backup import backup_local,restore_local
        self.ok(self.progress.discover('S','ordered',['p1'],'cursor-1','overlap one'))
        self.ok(self.progress.begin_attempt('S','p1'))
        self.ok(self.progress.fail('S','p1','network',retryable=True))
        backup=self.path.parent/'backup.sqlite3';restored=self.path.parent/'restored.sqlite3'
        self.ok(backup_local(self.path,backup));self.ok(restore_local(backup,restored))
        runner=Runner(restored,clock=lambda:self.time)
        token=self.ok(runner.resume('run','restored-owner'))['token']
        progress=runner.progress('run',token)
        self.assertEqual(progress.current('S')['gaps'],['p1'])
        self.assertEqual(self.ok(progress.begin_attempt('S','p1'))['attempt'],2)
        self.assertEqual(progress.begin_attempt('S','p1')['error']['code'],'ATTEMPT_PENDING')


if __name__=='__main__':unittest.main()
