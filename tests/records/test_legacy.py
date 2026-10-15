import shutil
from pathlib import Path
from test_source import StoreCase
from records.legacy import preview_legacy, apply_preview
from records.service import ResearchStore


class LegacyTests(StoreCase):
    def setUp(self):
        super().setUp()
        self.root = self.path.parent / 'legacy'
        (self.root/'sources').mkdir(parents=True)
        fixture = Path(__file__).resolve().parents[1]/'fixtures/records'
        shutil.copy(fixture/'legacy-source.md', self.root/'sources/CN-LEGACY.md')

    def test_preview_and_application_preserve_provenance(self):
        preview = self.value(preview_legacy(self.root))
        self.assertEqual(preview['unresolved'], [])
        record = preview['records'][0]
        self.assertEqual(record['id'], 'CN-LEGACY')
        self.assertIsNone(record['lastSuccess'])
        self.assertEqual(record['legacy']['firstCollectedAt'], '2026-10-14')
        self.value(apply_preview(self.root, preview, self.path, 'migration'))
        result = self.value(ResearchStore(self.path).read_record('CN-LEGACY'))['record']
        self.assertIn('没有讨论采样', result['legacy']['originalText'])
        self.value(apply_preview(self.root, preview, self.path, 'migration'))
        self.assertEqual(len(self.value(self.store.list_history('CN-LEGACY'))['items']), 1)

    def test_new_or_changed_files_reject_stale_preview(self):
        preview = self.value(preview_legacy(self.root))
        (self.root/'sources/new.md').write_text('new source')
        result = apply_preview(self.root, preview, self.path, 'migration')
        self.assertEqual(result['error']['code'], 'REVISION_CONFLICT')
        self.assertEqual(self.value(self.store.list_records())['items'], [])

    def test_unmapped_prose_is_reported_and_not_applied(self):
        (self.root/'ideas').mkdir()
        fixture = Path(__file__).resolve().parents[1]/'fixtures/records/legacy-idea.md'
        shutil.copy(fixture, self.root/'ideas/IDEA-LEGACY.md')
        preview = self.value(preview_legacy(self.root))
        self.assertEqual(preview['unresolved'][0]['path'], 'ideas/IDEA-LEGACY.md')
        self.assertFalse(apply_preview(self.root, preview, self.path, 'migration')['ok'])
