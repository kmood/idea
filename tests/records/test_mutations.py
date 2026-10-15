import concurrent.futures
import unittest
from test_source import StoreCase, source
from records.service import ResearchStore


class MutationTests(StoreCase):
    def test_replay_conflict_and_noop(self):
        original = self.value(self.store.create_research(source(), 'create'))
        patch = dict(name='新名字')
        updated = self.value(self.store.patch_research('CN-TEST', 1, patch, '修正', 'update'))
        self.assertEqual(updated['revision'], 2)
        other = ResearchStore(self.path)
        self.assertEqual(self.value(other.patch_research('CN-TEST', 1, patch, '修正', 'update')), updated)
        self.assertEqual(other.patch_research('CN-TEST', 2, patch, '不同意图', 'update')['error']['code'], 'IDEMPOTENCY_CONFLICT')
        self.assertEqual(self.value(other.patch_research('CN-TEST', 2, patch, '无变化', 'noop')), updated)
        self.assertEqual(len(self.value(other.list_history('CN-TEST'))['items']), 2)
        self.assertEqual(original['revision'], 1)

    def test_concurrent_expected_revision_has_one_winner(self):
        self.value(self.store.create_research(source(), 'create'))
        stores = [ResearchStore(self.path), ResearchStore(self.path)]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda i: stores[i].patch_research('CN-TEST', 1, {'name': str(i)}, 'change', str(i)), range(2)))
        self.assertEqual(sum(r['ok'] for r in results), 1)
        self.assertEqual([r['error']['code'] for r in results if not r['ok']], ['REVISION_CONFLICT'])

    def test_failed_access_cannot_advance_success(self):
        self.value(self.store.create_research(source(), 'create'))
        result = self.store.patch_research('CN-TEST', 1, {'accessStatus': 'failed', 'lastSuccess': '2026-10-15T00:00:00Z'}, 'failure', 'bad')
        self.assertEqual(result['error']['code'], 'VALIDATION_ERROR')
