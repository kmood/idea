import json
from pathlib import Path
from test_source import StoreCase
from records.legacy import preview_legacy, apply_preview, inventory
from records.exchange import Exchange
from records.backup import backup_local, restore_local
from records.personal import PersonalStore
from records.service import ResearchStore


class AcceptanceTests(StoreCase):
    def test_current_repository_migration_roundtrip_and_recovery(self):
        root = Path(__file__).resolve().parents[2]
        mapping = json.loads((root/'research/migrations/2026-10-15-records-map.json').read_text())
        before = inventory(root)
        preview = self.value(preview_legacy(root, mapping))
        self.assertEqual(preview['unresolved'], [])
        migrated = self.value(apply_preview(root, preview, self.path, 'rehearsal'))
        self.assertEqual(len(migrated['recordIds']), 18)
        for id in ('CN01', 'CN05', 'GL03', 'GL04', 'IDEA-20261015-001', 'TREND-20261015-001'):
            record = self.value(self.store.read_record(id))['record']
            self.assertTrue(record['legacy']['originalText'])
        cn05 = self.value(self.store.read_record('CN05'))['record']
        self.assertIsNone(cn05['lastSuccess'])
        evidence = self.value(self.store.read_record('EV-20261015-001'))['record']
        self.assertIsNone(evidence['publishedAt'])
        self.assertEqual(evidence['legacy']['dates']['publishedAt'], '2023-04-18')
        personal = PersonalStore(self.path)
        self.value(personal.set_personal_state('IDEA-20261015-001', None, {'favorite': True, 'notes': 'PRIVATE-ACCEPTANCE'}, 'p'))
        export = self.path.parent/'export.json'
        self.value(Exchange(self.path).export_research(export))
        self.assertNotIn('PRIVATE-ACCEPTANCE', export.read_text())
        replica = self.path.parent/'replica.sqlite3'
        self.value(Exchange(replica).import_research(json.loads(export.read_text()), 'import'))
        self.assertEqual(len(self.value(ResearchStore(replica).list_records(limit=100))['items']), 18)
        backup, restored = self.path.parent/'backup.sqlite3', self.path.parent/'restored.sqlite3'
        self.value(backup_local(self.path, backup)); self.value(restore_local(backup, restored))
        self.assertTrue(self.value(PersonalStore(restored).read_record('IDEA-20261015-001'))['favorite'])
        self.assertEqual(self.value(apply_preview(root, preview, restored, 'rehearsal')), migrated)
        self.assertEqual(inventory(root), before)
