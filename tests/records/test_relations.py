from test_source import StoreCase, source
from test_evidence import evidence, idea, trend
from records.personal import PersonalStore
from records.relations import Relations


class RelationTests(StoreCase):
    def setUp(self):
        super().setUp()
        for n, record in enumerate([source(), evidence(), idea('A'), idea('B'), idea('C'), trend('T')]):
            self.value(self.store.create_research(record, str(n)))
        self.relations = Relations(self.path)

    def test_merge_unmerge_preserve_personal_choices_and_history(self):
        personal = PersonalStore(self.path)
        self.value(personal.set_personal_state('A', None, {'favorite': True}, 'a'))
        self.value(personal.set_personal_state('B', None, {'ignored': True}, 'b'))
        self.value(self.relations.merge_records('A', 'B', 1, 1, '重复', 'merge'))
        self.assertEqual(self.value(self.store.read_record('A'))['canonicalId'], 'B')
        canonical = self.value(personal.related_states('B'))
        self.assertTrue(canonical['conflict'])
        self.assertEqual(set(canonical['states']), {'A', 'B'})
        self.assertEqual(len(self.value(self.store.list_records(kind='Idea'))['items']), 2)
        self.assertFalse(self.relations.merge_records('B', 'A', 2, 2, 'loop', 'loop')['ok'])
        self.value(self.relations.unmerge_records('A', 'B', 2, 2, '误合并', 'undo'))
        self.assertEqual(self.value(self.store.read_record('A'))['canonicalId'], 'A')
        self.assertEqual(len(self.value(self.store.list_history('A'))['items']), 3)
        self.assertTrue(self.value(personal.read_record('A'))['favorite'])

    def test_reject_wrong_type_self_conflict_and_link_derived(self):
        for source_id, target, sv, tv in [('A', 'T', 1, 1), ('A', 'A', 1, 1), ('A', 'B', 2, 1)]:
            self.assertFalse(self.relations.merge_records(source_id, target, sv, tv, 'bad', 'bad')['ok'])
        self.value(self.relations.link_derived_idea('T', 'A', 1, 1, 'derive'))
        self.assertEqual(self.value(self.store.read_record('A'))['record']['derivedFrom'], ['T'])
        self.assertEqual(self.value(self.store.read_record('T'))['record']['kind'], 'Trend')
