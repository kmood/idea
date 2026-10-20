import copy
import tempfile
import unittest
from pathlib import Path

from records.service import ResearchStore
from research.analysis import Analyzer
from research.reader import Reader
from research.runner import Runner


class PublicationTests(unittest.TestCase):
    def ok(self, result):
        self.assertTrue(result['ok'], result)
        return result['value']

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'db.sqlite3'
        self.time = 1000
        self.runner = Runner(self.path, clock=lambda: self.time)
        self.token = self.ok(self.runner.start('run', 'owner', [], []))['token']
        bridge = self.runner.bridge('run', self.token)
        source = dict(id='S', kind='Source', name='Forum', url='https://example.com',
                      audience=['teachers'], languages=['en'], accessStatus='untried',
                      lastAttempt=None, lastSuccess=None)
        self.ok(bridge.register_source(source, 'source'))
        self.ok(bridge.request('search', 'education terminology', tool='synthetic'))
        search = dict(status='completed', reason=None, discoveries=[dict(
            sourceId='S', url='https://example.com/thread', title='Terminology help',
            snippet='Discovery only')])
        self.candidate = self.ok(bridge.submit('search', search))['candidateIds'][0]

        class Fetch:
            def fetch(self, *args, **kwargs):
                return dict(ok=True, value=dict(
                    originalUrl='https://example.com/thread', finalUrl='https://example.com/thread',
                    headers={'content-type': 'text/plain'},
                    body=b'A teacher requests consistent terminology review.'))

        receipt = self.ok(Reader(self.runner.store, 'run', self.token, fetcher=Fetch()).read(
            'S', 'https://example.com/thread', self.candidate))['receipt']
        block = receipt['data']['blocks'][0]['blockId']
        self.draft = dict(
            candidateId=self.candidate, disposition='idea', reason='Specific audience and need',
            nextCondition=None, unknowns=['Willingness to pay', 'Cost'], counterEvidence=[], target=None,
            claims=[dict(text='A teacher requests consistent terminology review', nature='author_claim',
                         level='E1', refs=[dict(receiptId=receipt['id'], blockIds=[block])],
                         independence=[], payment=None, rebutsClaim=None)],
            content=dict(title='Terminology review service', audience='teachers',
                         problem='Inconsistent terminology', earningHypothesis='Charge per review; hypothesis',
                         industry=['education'], sideHustleTypes=['service'], markets=['overseas'], cost=None))
        self.validated = self.ok(Analyzer(self.runner.store, 'run', self.token).validate(self.draft))
        self.publication = self.runner.publication('run', self.token)
        self.store = ResearchStore(self.path)

    def test_manifest_precedes_business_steps_and_resume_completes_once(self):
        prepared = self.ok(self.publication.prepare(self.validated, 'location:thread-1'))
        manifest_id = prepared['manifest']['id']
        self.assertTrue(all(step['result'] is None for step in prepared['manifest']['data']['steps']))
        self.assertFalse(self.store.list_records('Evidence')['value']['items'])
        self.assertFalse(self.store.list_records('Idea')['value']['items'])

        partial = self.ok(self.publication.resume(manifest_id, max_steps=1))
        self.assertEqual(partial['status'], 'partial')
        manifest = self.ok(self.store.read_record(manifest_id))['record']
        self.assertIsNotNone(manifest['data']['steps'][0]['result'])
        self.assertIsNone(manifest['data']['steps'][1]['result'])
        self.assertEqual(len(self.ok(self.store.list_records('Evidence'))['items']), 1)
        self.assertFalse(self.store.list_records('Idea')['value']['items'])
        prepared_again = self.ok(self.publication.prepare(self.validated, 'location:thread-1'))
        self.assertIsNotNone(prepared_again['manifest']['data']['steps'][0]['result'])

        completed = self.ok(self.runner.publication('run', self.token).resume(manifest_id))
        self.assertEqual(completed['status'], 'complete')
        self.assertEqual(len(self.ok(self.store.list_records('Idea'))['items']), 1)
        outcome = self.ok(self.store.read_record(completed['outcomeId']))['record']
        self.assertEqual(outcome['data']['status'], 'idea')
        self.assertEqual(len(outcome['data']['recordRefs']), 2)
        replay = self.ok(self.publication.resume(manifest_id))
        self.assertEqual(replay, completed)
        for step in completed['manifest']['data']['steps']:
            self.assertEqual(len(self.ok(self.store.list_history(step['targetId']))['items']), 1)

    def test_backup_after_evidence_resumes_without_new_ids(self):
        from records.backup import backup_local, restore_local

        prepared = self.ok(self.publication.prepare(self.validated, 'location:thread-1'))
        manifest_id = prepared['manifest']['id']
        partial = self.ok(self.publication.resume(manifest_id, max_steps=1))
        original_targets = [step['targetId'] for step in partial['manifest']['data']['steps']]
        backup = self.path.parent / 'backup.sqlite3'
        restored = self.path.parent / 'restored.sqlite3'
        self.ok(backup_local(self.path, backup))
        self.ok(restore_local(backup, restored))
        runner = Runner(restored, clock=lambda: self.time)
        token = self.ok(runner.resume('run', 'restored-owner'))['token']
        completed = self.ok(runner.publication('run', token).resume(manifest_id))
        self.assertEqual([step['targetId'] for step in completed['manifest']['data']['steps']],
                         original_targets)
        self.assertEqual(completed['status'], 'complete')

    def test_changed_draft_creates_new_manifest_linked_to_old(self):
        first = self.ok(self.publication.prepare(self.validated, 'location:thread-1'))
        changed = copy.deepcopy(self.draft)
        changed['content']['title'] = 'Terminology QA service'
        validated = self.ok(Analyzer(self.runner.store, 'run', self.token).validate(changed))
        second = self.ok(self.publication.prepare(validated, 'location:thread-1'))
        self.assertNotEqual(first['manifest']['id'], second['manifest']['id'])
        self.assertEqual(second['manifest']['data']['supersedes']['recordId'], first['manifest']['id'])
        self.assertNotEqual([s['targetId'] for s in first['manifest']['data']['steps']],
                            [s['targetId'] for s in second['manifest']['data']['steps']])
        old = self.ok(self.store.read_record(first['manifest']['id']))['record']
        self.assertTrue(all(step['result'] is None for step in old['data']['steps']))

    def test_same_draft_replays_and_stale_owner_cannot_resume(self):
        first = self.ok(self.publication.prepare(self.validated, 'location:thread-1'))
        self.assertEqual(first, self.ok(self.publication.prepare(self.validated, 'location:thread-1')))
        self.time += 91
        token = self.ok(self.runner.store.execution.acquire('run', 'replacement'))
        self.assertEqual(self.publication.resume(first['manifest']['id'])['error']['code'], 'LEASE_EXPIRED')
        completed = self.ok(self.runner.publication('run', token).resume(first['manifest']['id']))
        self.assertEqual(completed['status'], 'complete')

    def test_deferred_publishes_only_manifest_and_outcome(self):
        draft = copy.deepcopy(self.draft)
        draft.update(disposition='deferred', claims=[], content=None,
                     nextCondition='Read the discussion when access returns')
        validated = self.ok(Analyzer(self.runner.store, 'run', self.token).validate(draft))
        prepared = self.ok(self.publication.prepare(validated, 'location:thread-1'))
        self.assertEqual(len(prepared['manifest']['data']['steps']), 1)
        completed = self.ok(self.publication.resume(prepared['manifest']['id']))
        self.assertEqual(completed['status'], 'complete')
        self.assertFalse(self.store.list_records('Evidence')['value']['items'])
        self.assertFalse(self.store.list_records('Idea')['value']['items'])

    def test_typed_counter_evidence_is_published_and_linked(self):
        draft = copy.deepcopy(self.draft)
        draft['counterEvidence'] = [dict(
            text='A teacher says their terminology is already consistent', nature='author_claim', level='E1',
            refs=self.draft['claims'][0]['refs'], rebutsClaim='All teachers need terminology repair')]
        validated = self.ok(Analyzer(self.runner.store, 'run', self.token).validate(draft))
        prepared = self.ok(self.publication.prepare(validated, 'location:thread-1'))
        completed = self.ok(self.publication.resume(prepared['manifest']['id']))
        evidence = self.ok(self.store.list_records('Evidence'))['items']
        self.assertEqual(len(evidence), 2)
        self.assertEqual(next(item for item in evidence if item['rebutsClaim'])['rebutsClaim'],
                         'All teachers need terminology repair')
        outcome = self.ok(self.store.read_record(completed['outcomeId']))['record']
        self.assertEqual(len(outcome['data']['recordRefs']), 3)

    def test_resume_after_business_commit_before_manifest_confirmation(self):
        from records.publishing import ResearchPublisher
        from research.publication import intent_for

        prepared = self.ok(self.publication.prepare(self.validated, 'location:thread-1'))
        manifest_id = prepared['manifest']['id']
        plan = self.ok(self.runner.store.publication_plan('run', manifest_id, token=self.token))
        step = plan['steps'][0]
        public_step = prepared['manifest']['data']['steps'][0]
        intent_id = 'publication:' + manifest_id + ':' + step['stepId']
        intent = intent_for(step['request'], public_step['operationId'])
        self.ok(self.runner.store.save_intent('run', intent_id, intent, token=self.token))
        self.ok(ResearchPublisher(self.runner.store).publish_step(
            'run', self.token, intent_id, step['request']))
        manifest = self.ok(self.store.read_record(manifest_id))['record']
        self.assertIsNone(manifest['data']['steps'][0]['result'])
        completed = self.ok(self.publication.resume(manifest_id))
        evidence_id = completed['manifest']['data']['steps'][0]['targetId']
        self.assertEqual(len(self.ok(self.store.list_history(evidence_id))['items']), 1)

    def test_resume_rejects_changed_manifest_commitments(self):
        prepared = self.ok(self.publication.prepare(self.validated, 'location:thread-1'))
        manifest = prepared['manifest']
        steps = copy.deepcopy(manifest['data']['steps'])
        steps[0]['operationId'] = 'publish:changed-operation'
        self.ok(self.store.patch_research(manifest['id'], manifest['revision'],
                                          {'data': manifest['data'] | {'steps': steps}},
                                          'Simulate conflicting manifest writer', 'change-manifest'))
        result = self.publication.resume(manifest['id'])
        self.assertEqual(result['error']['code'], 'VALIDATION_ERROR')
        self.assertFalse(self.store.list_records('Evidence')['value']['items'])

    def test_update_adds_evidence_without_replacing_existing_history(self):
        receipt_id = self.draft['claims'][0]['refs'][0]['receiptId']
        receipt = self.ok(self.store.read_record(receipt_id))['record']
        legacy = dict(id='E-OLD', kind='Evidence', sourceId='S', url='https://example.com/thread',
                      claim='Earlier observation', summary='Earlier observation', publishedAt=None,
                      accessedAt=receipt['data']['fetchedAt'], nature='author_claim', level='E1',
                      paymentSignal=None, rebutsClaim=None)
        self.ok(self.store.create_research(legacy, 'old-evidence'))
        trend = dict(id='T', kind='Trend', title='Existing trend', summary='Earlier summary',
                     evidenceIds=['E-OLD'], impact=dict(nature='inference', text='Unknown impact'),
                     questions=['Who pays?'])
        self.ok(self.store.create_research(trend, 'old-trend'))
        draft = copy.deepcopy(self.draft)
        draft.update(disposition='update', target=dict(recordId='T', revision=1),
                     content=dict(summary='New observed terminology request'))
        validated = self.ok(Analyzer(self.runner.store, 'run', self.token).validate(draft))
        prepared = self.ok(self.publication.prepare(validated, 'location:thread-1'))
        completed = self.ok(self.publication.resume(prepared['manifest']['id']))
        updated = self.ok(self.store.read_record('T'))['record']
        self.assertEqual(updated['revision'], 2)
        self.assertEqual(updated['summary'], 'New observed terminology request')
        self.assertEqual(updated['evidenceIds'][0], 'E-OLD')
        self.assertEqual(len(updated['evidenceIds']), 2)
        self.assertEqual(self.ok(self.store.read_record(completed['outcomeId']))['record']['data']['status'],
                         'update')


if __name__ == '__main__':
    unittest.main()
