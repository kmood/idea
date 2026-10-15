import copy
import json
from test_source import StoreCase, source
from test_evidence import evidence, idea
from records.exchange import Exchange, digest
from records.service import ResearchStore
from records.personal import PersonalStore


class ImportTests(StoreCase):
    def setUp(self):
        super().setUp()
        for i, record in enumerate((source(), evidence(), idea())):
            self.value(self.store.create_research(record, str(i)))
        self.exchange = Exchange(self.path)
        self.file = self.path.parent / 'public.json'
        self.value(self.exchange.export_research(self.file))
        self.bundle = json.loads(self.file.read_text())
        self.other_path = self.path.parent / 'other.sqlite3'
        self.other = Exchange(self.other_path)

    def test_roundtrip_replay_and_personal_preservation(self):
        self.value(self.other.import_research(self.bundle, 'import'))
        private = PersonalStore(self.other_path)
        saved = self.value(private.set_personal_state('IDEA-TEST', None, {'notes': 'PRIVATE'}, 'personal'))
        self.value(self.other.import_research(self.bundle, 'again'))
        research = ResearchStore(self.other_path)
        original = self.value(research.read_record('CN-TEST'))['record']
        self.assertEqual(self.value(research.create_research(source(), '0')), original)
        self.value(self.store.patch_research('CN-TEST', 1, {'name': 'new'}, 'change', 'update'))
        self.value(self.exchange.export_research(self.file))
        self.value(self.other.import_research(json.loads(self.file.read_text()), 'next'))
        self.assertEqual(self.value(private.read_record('IDEA-TEST')), saved)
        output = self.path.parent / 'roundtrip.json'
        self.value(self.other.export_research(output))
        self.assertEqual(output.read_bytes(), self.file.read_bytes())

    def test_bad_bundle_rolls_back_whole_import(self):
        variants = []
        bad = copy.deepcopy(self.bundle); bad['data']['records'][0]['notes'] = 'PRIVATE'; variants.append(bad)
        bad = copy.deepcopy(self.bundle); bad['data']['versions'].pop(); variants.append(bad)
        bad = copy.deepcopy(self.bundle); bad['data']['events'][0]['after']['revision'] = 99; variants.append(bad)
        bad = copy.deepcopy(self.bundle); bad['data']['records'].append(bad['data']['records'][0]); variants.append(bad)
        bad = copy.deepcopy(self.bundle)
        for record in bad['data']['records'] + bad['data']['versions']:
            if record['kind'] == 'Evidence': record['sourceId'] = 'MISSING'
        variants.append(bad)
        for bad in variants:
            bad['bundleId'] = digest({k:v for k,v in bad.items() if k != 'bundleId'})
            self.assertFalse(self.other.import_research(bad, 'bad')['ok'])
            self.assertEqual(self.value(ResearchStore(self.other_path).list_records())['items'], [])

    def test_unexported_edits_and_divergent_history_are_rejected(self):
        self.value(self.other.import_research(self.bundle, 'initial'))
        local = ResearchStore(self.other_path)
        self.value(local.patch_research('CN-TEST', 1, {'name': 'local'}, 'local', 'local'))
        self.value(self.store.patch_research('CN-TEST', 1, {'name': 'remote'}, 'remote', 'remote'))
        self.value(self.exchange.export_research(self.file))
        newer = json.loads(self.file.read_text())
        self.assertEqual(self.other.import_research(newer, 'next')['error']['code'], 'REVISION_CONFLICT')
        self.value(self.other.export_research(self.path.parent / 'local.json'))
        self.assertEqual(self.other.import_research(newer, 'next')['error']['code'], 'REVISION_CONFLICT')
