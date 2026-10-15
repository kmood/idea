"""Migration must preserve the source and publish only validated copies."""
import sqlite3
from contextlib import closing
from unittest.mock import patch
from test_source import StoreCase, source
from records.contracts import Fault
from records.storage import Database
from records.personal import PersonalStore
from records.service import ResearchStore
from records.backup import backup_local


class SchemaUpgradeTests(StoreCase):
    def legacy(self):
        self.value(self.store.create_research(source(), 'create'))
        private = self.value(PersonalStore(self.path).set_personal_state(
            'CN-TEST', None, {'notes': 'PRIVATE'}, 'personal'))
        with closing(self.store.db.connect()) as conn:
            conn.execute("UPDATE metadata SET value='1' WHERE key='schemaVersion'")
            conn.execute("DELETE FROM metadata WHERE key='dbInstanceId'")
        return private

    def test_upgrade_preserves_history_private_state_and_replay(self):
        from records.migrations import upgrade_database
        private = self.legacy()
        original = self.path.read_bytes()
        target = self.path.parent / 'v2.sqlite3'
        self.value(upgrade_database(self.path, target))
        self.assertEqual(self.path.read_bytes(), original)
        store = ResearchStore(target)
        self.assertEqual(self.value(PersonalStore(target).read_record('CN-TEST')), private)
        record = self.value(store.create_research(source(), 'create'))
        self.assertEqual(record['revision'], 1)
        self.assertEqual(len(self.value(store.list_history('CN-TEST'))['items']), 1)
        self.value(store.create_research(source('CN-NEW'), 'new'))
        with closing(store.db.connect()) as conn:
            self.assertEqual(conn.execute("SELECT value FROM metadata WHERE key='schemaVersion'").fetchone()[0], '2')
        self.value(backup_local(target, self.path.parent / 'backup.sqlite3'))

    def test_old_database_requires_explicit_upgrade_without_writes(self):
        self.legacy()
        before = self.path.read_bytes()
        with self.assertRaises(Fault):
            Database(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_unknown_version_rejected_before_schema_creation(self):
        unknown = self.path.parent / 'future.sqlite3'
        with closing(sqlite3.connect(unknown, autocommit=True)) as conn:
            conn.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            conn.execute("INSERT INTO metadata VALUES ('schemaVersion', '99')")
        before = unknown.read_bytes()
        with self.assertRaises(Fault):
            Database(unknown)
        self.assertEqual(unknown.read_bytes(), before)

    def test_failed_migration_never_publishes_partial_destination(self):
        from records.migrations import upgrade_database
        self.legacy()
        before = self.path.read_bytes()
        target = self.path.parent / 'failed.sqlite3'
        with patch('records.migrations.migrate_v1', side_effect=Fault('VALIDATION_ERROR')):
            self.assertFalse(upgrade_database(self.path, target)['ok'])
        self.assertFalse(target.exists())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(list(self.path.parent.glob('.records-upgrade-*')))

    def test_upgrade_refuses_existing_destination(self):
        from records.migrations import upgrade_database
        self.legacy()
        self.assertFalse(upgrade_database(self.path, self.path)['ok'])
