"""Synthetic records only; all databases live in temporary directories."""
import tempfile
import unittest
from pathlib import Path
from records.service import ResearchStore


def source(id='CN-TEST'):
    return dict(id=id, kind='Source', name='合成来源', url='https://example.com',
                audience=['商家'], languages=['zh'], accessStatus='readable',
                lastAttempt=None, lastSuccess=None)


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'records.sqlite3'
        self.store = ResearchStore(self.path)

    def value(self, result):
        self.assertTrue(result['ok'], result)
        return result['value']


class SourceTests(StoreCase):
    def test_reopen_preserves_record_and_first_history(self):
        created = self.value(self.store.create_research(source(), 'create'))
        reopened = ResearchStore(self.path)
        self.assertEqual(self.value(reopened.read_record('CN-TEST'))['record'], created)
        events = self.value(reopened.list_history('CN-TEST'))['items']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['after'], {'recordId': 'CN-TEST', 'revision': 1})
        self.assertEqual(created['revision'], 1)
        self.assertIsNone(created['lastSuccess'])

    def test_invalid_or_unknown_fields_are_rejected_without_history(self):
        for patch in ({'url': ''}, {'name': None}, {'favorite': True}, {'extra': 'bad'},
                      {'languages': 'zh'}, {'lastSuccess': 'yesterday'}):
            with self.subTest(patch=patch):
                result = self.store.create_research(source() | patch, 'bad')
                self.assertFalse(result['ok'])
        self.assertEqual(self.store.read_record('CN-TEST')['error']['code'], 'NOT_FOUND')

    def test_duplicate_id_does_not_overwrite(self):
        self.value(self.store.create_research(source(), 'one'))
        self.assertEqual(self.store.create_research(source(), 'two')['error']['code'], 'DUPLICATE_ID')
