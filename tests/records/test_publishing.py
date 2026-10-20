import tempfile
import unittest
from pathlib import Path

from records.exchange import digest
from records.runtime import ResearchRuntimeStore
from records.service import ResearchStore
from research.reader import Reader
from research.runner import Runner


class PublishingTests(unittest.TestCase):
    def ok(self, result):
        self.assertTrue(result['ok'], result)
        return result['value']

    def setUp(self):
        from records.publishing import ResearchPublisher

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'db.sqlite3'
        self.time = 1000
        self.runner = Runner(self.path, clock=lambda: self.time)
        self.token = self.ok(self.runner.start('run', 'owner', [], []))['token']
        self.store = ResearchStore(self.path)
        source = dict(id='S', kind='Source', name='Forum', url='https://example.com',
                      audience=['teachers'], languages=['en'], accessStatus='untried',
                      lastAttempt=None, lastSuccess=None)
        self.ok(self.store.create_research(source, 'source'))

        class Fetch:
            def fetch(self, *args, **kwargs):
                return dict(ok=True, value=dict(
                    originalUrl='https://example.com/thread', finalUrl='https://example.com/thread',
                    headers={'content-type': 'text/plain'}, body=b'A teacher needs terminology review.'))

        receipt = self.ok(Reader(self.runner.store, 'run', self.token, fetcher=Fetch()).read(
            'S', 'https://example.com/thread', 'candidate'))['receipt']
        block = receipt['data']['blocks'][0]['blockId']
        observation = dict(receiptId=receipt['id'], blockIds=[block], replyIds=[], independence=[],
                           precision='unknown', dateBasis=None, paymentVerification=None)
        self.record = dict(id='E', kind='Evidence', sourceId='S', url='https://example.com/thread',
                           claim='A teacher requests terminology review', summary='Specific request',
                           publishedAt=None, accessedAt=receipt['data']['fetchedAt'], nature='author_claim',
                           level='E1', paymentSignal=None, rebutsClaim=None, observation=observation)
        self.request = dict(action='create', record=self.record, reason='Validated analysis claim')
        self.intent = dict(recordId='E', operationId='publish:E', requestHash=digest(self.request),
                           expectedRevision=None)
        self.ok(self.runner.store.save_intent('run', 'step:E', self.intent, token=self.token))
        self.publisher = ResearchPublisher(self.runner.store)

    def test_create_is_atomic_and_replays_after_lost_response(self):
        first = self.ok(self.publisher.publish_step('run', self.token, 'step:E', self.request))
        second = self.ok(self.publisher.publish_step('run', self.token, 'step:E', self.request))
        self.assertEqual(first, second)
        self.assertEqual(first['record']['id'], 'E')
        self.assertEqual(first['result'], {'recordId': 'E', 'revision': 1})
        self.assertEqual(len(self.ok(self.store.list_history('E'))['items']), 1)
        inspected = self.ok(self.runner.store.inspect_run('run'))['intents'][0]
        self.assertEqual(inspected['status'], 'completed')
        self.assertEqual(inspected['result'], {'recordId': 'E', 'revision': 1})

    def test_failure_before_commit_rolls_back_record_history_operation_and_receipt(self):
        def fail(_conn):
            raise RuntimeError('simulated process failure')

        self.publisher.before_commit = fail
        with self.assertRaises(RuntimeError):
            self.publisher.publish_step.__wrapped__(self.publisher, 'run', self.token, 'step:E', self.request)
        self.assertFalse(self.store.read_record('E')['ok'])
        inspected = self.ok(self.runner.store.inspect_run('run'))['intents'][0]
        self.assertEqual(inspected['status'], 'pending')
        self.publisher.before_commit = None
        self.ok(self.publisher.publish_step('run', self.token, 'step:E', self.request))

    def test_request_change_stale_owner_and_wrong_target_are_rejected(self):
        changed = dict(self.request, reason='Different request')
        self.assertEqual(self.publisher.publish_step('run', self.token, 'step:E', changed)['error']['code'],
                         'IDEMPOTENCY_CONFLICT')
        wrong = dict(self.request, record=dict(self.record, id='OTHER'))
        self.assertFalse(self.publisher.publish_step('run', self.token, 'step:E', wrong)['ok'])
        self.time += 91
        replacement = self.ok(self.runner.store.execution.acquire('run', 'replacement'))
        self.assertEqual(self.publisher.publish_step('run', self.token, 'step:E', self.request)['error']['code'],
                         'LEASE_EXPIRED')
        self.ok(self.publisher.publish_step('run', replacement, 'step:E', self.request))

    def test_unread_blocks_personal_fields_and_assessment_cannot_publish(self):
        bad = dict(self.record)
        bad['observation'] = dict(bad['observation'], blockIds=['invented'])
        request = dict(self.request, record=bad)
        intent = dict(recordId='E2', operationId='publish:E2', requestHash=digest(request), expectedRevision=None)
        request['record'] = dict(request['record'], id='E2')
        intent['requestHash'] = digest(request)
        self.ok(self.runner.store.save_intent('run', 'step:E2', intent, token=self.token))
        self.assertFalse(self.publisher.publish_step('run', self.token, 'step:E2', request)['ok'])

        bad_reply = dict(self.record, id='E3')
        bad_reply['observation'] = dict(bad_reply['observation'], replyIds=['unread-reply'])
        request = dict(self.request, record=bad_reply)
        intent = dict(recordId='E3', operationId='publish:E3', requestHash=digest(request),
                      expectedRevision=None)
        self.ok(self.runner.store.save_intent('run', 'step:E3', intent, token=self.token))
        self.assertFalse(self.publisher.publish_step('run', self.token, 'step:E3', request)['ok'])

        for extra in ('favorite', 'validationStage'):
            record = dict(self.record, id='E-' + extra, **{extra: True})
            request = dict(self.request, record=record)
            intent = dict(recordId=record['id'], operationId='publish:' + record['id'],
                          requestHash=digest(request), expectedRevision=None)
            self.ok(self.runner.store.save_intent('run', 'step:' + record['id'], intent, token=self.token))
            self.assertFalse(self.publisher.publish_step('run', self.token, 'step:' + record['id'], request)['ok'])

        assessment = dict(action='create', record=dict(id='assessment:X', kind='Assessment'), reason='No')
        intent = dict(recordId='assessment:X', operationId='publish:assessment',
                      requestHash=digest(assessment), expectedRevision=None)
        self.ok(self.runner.store.save_intent('run', 'step:assessment', intent, token=self.token))
        self.assertFalse(self.publisher.publish_step('run', self.token, 'step:assessment', assessment)['ok'])

    def test_existing_exact_id_is_reported_without_completing_intent(self):
        duplicate = dict(action='create', record=dict(
            id='S', kind='Source', name='Other', url='https://other.example', audience=['other'],
            languages=['en'], accessStatus='untried', lastAttempt=None, lastSuccess=None),
            reason='Conflicting identity')
        intent = dict(recordId='S', operationId='publish:duplicate-source',
                      requestHash=digest(duplicate), expectedRevision=None)
        self.ok(self.runner.store.save_intent('run', 'step:duplicate', intent, token=self.token))
        result = self.publisher.publish_step('run', self.token, 'step:duplicate', duplicate)
        self.assertEqual(result['error']['code'], 'DUPLICATE_ID')
        items = self.ok(self.runner.store.inspect_run('run'))['intents']
        saved = next(item for item in items if item['intentId'] == 'step:duplicate')
        self.assertEqual(saved['status'], 'pending')

    def test_patch_requires_exact_revision_and_records_one_update(self):
        self.ok(self.publisher.publish_step('run', self.token, 'step:E', self.request))
        patch_request = dict(action='patch', recordId='E', expectedRevision=1,
                             patch={'summary': 'Reviewed specific request'}, reason='Add reviewed summary')
        intent = dict(recordId='E', operationId='patch:E', requestHash=digest(patch_request), expectedRevision=1)
        self.ok(self.runner.store.save_intent('run', 'step:patch', intent, token=self.token))
        result = self.ok(self.publisher.publish_step('run', self.token, 'step:patch', patch_request))
        self.assertEqual(result['result'], {'recordId': 'E', 'revision': 2})
        self.assertEqual(len(self.ok(self.store.list_history('E'))['items']), 2)

        stale = dict(patch_request, patch={'summary': 'Stale overwrite'})
        stale_intent = dict(recordId='E', operationId='patch:stale', requestHash=digest(stale), expectedRevision=1)
        self.ok(self.runner.store.save_intent('run', 'step:stale', stale_intent, token=self.token))
        self.assertEqual(self.publisher.publish_step('run', self.token, 'step:stale', stale)['error']['code'],
                         'REVISION_CONFLICT')

    def test_backup_restore_keeps_completed_receipt_and_requires_new_owner(self):
        from records.backup import backup_local, restore_local
        from records.publishing import ResearchPublisher

        expected = self.ok(self.publisher.publish_step('run', self.token, 'step:E', self.request))
        backup = self.path.parent / 'backup.sqlite3'
        restored = self.path.parent / 'restored.sqlite3'
        self.ok(backup_local(self.path, backup))
        self.ok(restore_local(backup, restored))
        runtime = ResearchRuntimeStore(restored, clock=lambda: self.time)
        self.assertFalse(ResearchPublisher(runtime).publish_step(
            'run', self.token, 'step:E', self.request)['ok'])
        token = self.ok(runtime.execution.acquire('run', 'restored-owner'))
        self.assertEqual(self.ok(ResearchPublisher(runtime).publish_step(
            'run', token, 'step:E', self.request)), expected)


if __name__ == '__main__':
    unittest.main()
