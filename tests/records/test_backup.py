from pathlib import Path
from test_source import StoreCase, source
from records.backup import backup_local, restore_local
from records.personal import PersonalStore
from records.service import ResearchStore


class BackupTests(StoreCase):
    def test_restore_preserves_private_history_and_replay(self):
        original = self.value(self.store.create_research(source(), 'create'))
        private = PersonalStore(self.path)
        saved = self.value(private.set_personal_state('CN-TEST', None, {'notes': 'PRIVATE'}, 'personal'))
        backup = self.path.parent / 'backup.sqlite3'
        summary = self.value(backup_local(self.path, backup))
        restored = self.path.parent / 'restored.sqlite3'
        self.assertEqual(self.value(restore_local(backup, restored))['counts'], summary['counts'])
        self.assertEqual(self.value(PersonalStore(restored).read_record('CN-TEST')), saved)
        self.assertEqual(self.value(ResearchStore(restored).create_research(source(), 'create')), original)
        self.assertEqual(len(self.value(PersonalStore(restored).list_history('CN-TEST'))['items']), 1)

    def test_existing_destination_and_bad_backup_are_rejected(self):
        bad = self.path.parent / 'bad.sqlite3'; bad.write_text('not sqlite')
        target = self.path.parent / 'restore.sqlite3'
        self.assertFalse(restore_local(bad, target)['ok'])
        self.assertFalse(target.exists())
        self.assertFalse(backup_local(self.path, self.path)['ok'])
        self.assertEqual(ResearchStore(self.path).list_records()['value']['items'], [])
