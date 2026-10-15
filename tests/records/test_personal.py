from concurrent.futures import ThreadPoolExecutor
from test_source import StoreCase, source
from records.personal import PersonalStore


class PersonalTests(StoreCase):
    def setUp(self):
        super().setUp()
        self.value(self.store.create_research(source(), 'create'))
        self.personal = PersonalStore(self.path)

    def test_default_first_write_reopen_and_research_isolation(self):
        default = self.value(self.personal.read_record('CN-TEST'))
        self.assertIsNone(default['revision'])
        patch = dict(favorite=True, ignored=True, validationStage='准备验证', notes='PRIVATE-SENTINEL')
        saved = self.value(self.personal.set_personal_state('CN-TEST', None, patch, 'personal'))
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(self.value(PersonalStore(self.path).read_record('CN-TEST')), saved)
        self.value(self.store.patch_research('CN-TEST', 1, {'name': '新标题'}, '补充', 'update'))
        self.assertEqual(self.value(self.personal.read_record('CN-TEST')), saved)
        rejected = self.store.patch_research('CN-TEST', 2, {'notes': 'PRIVATE-SENTINEL'}, 'x', 'invalid')
        self.assertEqual(rejected['error']['code'], 'SCOPE_VIOLATION')
        self.assertNotIn('PRIVATE-SENTINEL', str(rejected))
        self.assertEqual(self.value(self.personal.set_personal_state('CN-TEST', None, patch, 'personal')), saved)

    def test_concurrent_initial_write_conflicts_and_history_is_private(self):
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda i: self.personal.set_personal_state('CN-TEST', None, {'notes': str(i)}, str(i)), range(2)))
        self.assertEqual(sum(r['ok'] for r in results), 1)
        self.assertEqual(len(self.value(self.personal.list_history('CN-TEST'))['items']), 1)
        self.assertEqual(len(self.value(self.store.list_history('CN-TEST'))['items']), 1)
        self.assertEqual(self.personal.set_personal_state('MISSING', None, {}, 'm')['error']['code'], 'NOT_FOUND')
