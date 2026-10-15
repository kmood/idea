from test_source import StoreCase, source
from test_evidence import evidence, idea


def assessment():
    return dict(fit='有条件适合', reasons={'时间': '需要确认'}, unknowns=['成本'], evidenceIds=['EV-TEST'], generatedAt='2026-10-15T00:00:00Z', cost=None)


class QueryTests(StoreCase):
    def seed(self):
        for n, record in enumerate([source(), evidence(), idea(), idea('IDEA-SECOND')]):
            self.value(self.store.create_research(record, str(n)))

    def test_assessment_independent_version_and_unknown_cost(self):
        self.seed()
        saved = self.value(self.store.save_assessment('IDEA-TEST', assessment(), None, 'a'))
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(self.value(self.store.read_record('IDEA-TEST'))['record']['revision'], 1)
        result = self.value(self.store.list_records(kind='Idea', query='合成', filters={'industry': '电商', 'market': '国内', 'evidence': 'E1', 'fit': '有条件适合', 'costUnknown': True}))
        self.assertEqual([x['id'] for x in result['items']], ['IDEA-TEST'])
        invalid = assessment() | {'cost': {'min': 0, 'max': 1}}
        self.assertFalse(self.store.save_assessment('IDEA-TEST', invalid, 1, 'bad')['ok'])
        self.assertEqual(self.store.save_assessment('IDEA-TEST', assessment(), None, 'conflict')['error']['code'], 'REVISION_CONFLICT')

    def test_list_and_history_pagination(self):
        self.seed()
        first = self.value(self.store.list_records(kind='Idea', limit=1))
        second = self.value(self.store.list_records(kind='Idea', limit=1, cursor=first['nextCursor']))
        self.assertNotEqual(first['items'][0]['id'], second['items'][0]['id'])
        self.assertIsNone(second['nextCursor'])
        self.assertEqual(self.value(self.store.list_records(filters={'costUnknown': False}))['items'], [])
        for i in range(3):
            self.value(self.store.patch_research('IDEA-TEST', i+1, {'title': str(i)}, 'update', 'u'+str(i)))
        first = self.value(self.store.list_history('IDEA-TEST', limit=2))
        second = self.value(self.store.list_history('IDEA-TEST', cursor=first['nextCursor'], limit=2))
        self.assertEqual(len({x['eventId'] for x in first['items']+second['items']}), 4)
        self.assertFalse(self.store.list_records(limit=101)['ok'])
