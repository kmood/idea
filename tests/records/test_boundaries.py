import copy
import json
from test_source import StoreCase, source
from records.exchange import Exchange, digest
from records.contracts import Fault


class BoundaryTests(StoreCase):
    def test_export_cannot_replace_database_or_existing_unrelated_file(self):
        self.value(self.store.create_research(source(), 'create'))
        result = Exchange(self.path).export_research(self.path)
        self.assertFalse(result['ok'])
        self.assertTrue(self.store.read_record('CN-TEST')['ok'])
        unrelated = self.path.parent/'notes.md'; unrelated.write_text('important')
        self.assertFalse(Exchange(self.path).export_research(unrelated)['ok'])
        self.assertEqual(unrelated.read_text(), 'important')

    def test_nested_malformed_bundle_returns_errors_not_tracebacks(self):
        self.value(self.store.create_research(source(), 'create'))
        file = self.path.parent/'public.json'
        self.value(Exchange(self.path).export_research(file))
        bundle = json.loads(file.read_text())
        for section, key in [('events', 'recordId'), ('events', 'operationId'), ('events', 'eventId'),
                             ('events', 'after'), ('operations', 'result'), ('operations', 'operationId'),
                             ('versions', 'kind'), ('records', 'id')]:
            for malformed in ([], {}, None, True):
                with self.subTest(section=section, key=key, value=malformed):
                    bad = copy.deepcopy(bundle)
                    bad['data'][section][0][key] = malformed
                    bad['bundleId'] = digest({k:v for k,v in bad.items() if k != 'bundleId'})
                    result = Exchange(self.path).import_research(bad, 'bad')
                    self.assertFalse(result['ok'])
                    self.assertEqual(result['error']['code'], 'VALIDATION_ERROR')

    def test_malformed_url_and_id_are_validation_errors(self):
        for bad in ({'url': 'https://['}, {'id': {}}, {'id': []}, {'accessStatus': []}):
            with self.subTest(bad=bad):
                result = self.store.create_research(source() | bad, 'bad')
                self.assertEqual(result['error']['code'], 'VALIDATION_ERROR')

    def test_record_contract_rejects_fake_verification_and_bad_optional_shapes(self):
        from test_evidence import evidence
        self.value(self.store.create_research(source(), 's'))
        for n, bad in enumerate(({'level': 'E3', 'paymentSignal': 'paid', 'nature': 'author_claim'},
                    {'level': 'E3', 'paymentSignal': None, 'nature': 'fact'},
                    {'legacy': None, 'accessedAt': None})):
            with self.subTest(bad=bad):
                self.assertFalse(self.store.create_research(evidence('EV-'+str(n)) | bad, 'e'+str(n))['ok'])
        self.assertFalse(self.store.list_records(filters=[])['ok'])
        self.assertFalse(self.store.read_record('CN-TEST', revision=True)['ok'])

    def test_export_detects_external_snapshot_changes(self):
        self.value(self.store.create_research(source(), 's'))
        exchange = Exchange(self.path)
        target = self.path.parent/'public.json'
        self.value(exchange.export_research(target))
        original = json.loads(target.read_text())
        other_path = self.path.parent/'other.sqlite3'
        other = Exchange(other_path)
        self.value(other.import_research(original, 'initial'))
        from records.service import ResearchStore
        self.value(ResearchStore(other_path).patch_research('CN-TEST', 1, {'name': 'remote'}, 'remote', 'r'))
        remote = self.path.parent/'remote.json'
        self.value(other.export_research(remote))
        target.write_bytes(remote.read_bytes())
        self.assertFalse(exchange.export_research(target)['ok'])
        self.assertEqual(target.read_bytes(), remote.read_bytes())
