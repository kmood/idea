import json
from unittest.mock import patch
from test_source import StoreCase, source
from records.exchange import Exchange
from records.personal import PersonalStore


class ExportTests(StoreCase):
    def test_deterministic_public_snapshot_and_atomic_failure(self):
        self.value(self.store.create_research(source(), 'create'))
        private = PersonalStore(self.path)
        self.value(private.set_personal_state('CN-TEST', None, {'notes': 'PRIVATE-SENTINEL'}, 'PRIVATE-OP'))
        exchange = Exchange(self.path)
        output = self.path.parent / 'research.json'
        first = self.value(exchange.export_research(output))
        original = output.read_bytes()
        self.assertNotIn(b'PRIVATE', original)
        self.assertEqual(self.value(exchange.export_research(output)), first)
        self.assertEqual(output.read_bytes(), original)
        payload = json.loads(original)
        self.assertEqual(len(payload['data']['events']), 1)
        self.assertEqual(len(payload['data']['operations']), 1)
        self.value(self.store.patch_research('CN-TEST', 1, {'name': 'changed'}, 'fix', 'update'))
        with patch('records.exchange.os.replace', side_effect=OSError('PRIVATE-ERROR')):
            failure = exchange.export_research(output)
        self.assertEqual(failure['error']['code'], 'STORAGE_ERROR')
        self.assertNotIn('PRIVATE-ERROR', str(failure))
        self.assertEqual(output.read_bytes(), original)
        self.assertNotEqual(self.value(exchange.export_research(output))['bundleId'], first['bundleId'])

    def test_status_distinguishes_unexported_research_from_private_changes(self):
        exchange = Exchange(self.path)
        self.value(self.store.create_research(source(), 'create'))
        self.assertTrue(self.value(exchange.status())['researchDirty'])
        self.value(exchange.export_research(self.path.parent/'status.json'))
        self.value(PersonalStore(self.path).set_personal_state('CN-TEST', None, {'notes': 'PRIVATE'}, 'p'))
        status = self.value(exchange.status())
        self.assertFalse(status['researchDirty'])
        self.assertEqual(status['privateStates'], 1)
        self.assertNotIn('PRIVATE', str(status))
