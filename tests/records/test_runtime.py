import json
from test_source import StoreCase
from records.backup import backup_local, restore_local
from records.exchange import Exchange


def request():
    return dict(sourceIds=['CN-TEST'], queries=['synthetic query'],
                limits=dict(searches=12,candidates=10,auxiliary=8,total=40),deadline='2026-10-19T01:00:00Z')


def intent():
    return dict(recordId='FUTURE',operationId='future-create',requestHash='a'*64,expectedRevision=None)


class RuntimeTests(StoreCase):
    def test_restart_preserves_run_intent_and_rejects_changed_requests(self):
        from records.runtime import ResearchRuntimeStore
        store = ResearchRuntimeStore(self.path)
        initial = self.value(store.begin('RUN-1',request()))
        saved = self.value(store.save_intent('RUN-1','STEP-1',intent()))
        reopened = ResearchRuntimeStore(self.path)
        self.assertEqual(self.value(reopened.begin('RUN-1',request())), initial)
        state = self.value(reopened.inspect_run('RUN-1'))
        self.assertEqual(state['run'],initial)
        self.assertEqual(state['intents'],[saved])
        self.assertFalse(reopened.begin('RUN-1', request() | {'queries':['different']})['ok'])
        self.assertFalse(reopened.save_intent('RUN-1','STEP-1',intent() | {'requestHash':'b'*64})['ok'])

    def test_backup_contains_runtime_and_public_snapshot_excludes_it(self):
        from records.runtime import ResearchRuntimeStore
        store = ResearchRuntimeStore(self.path)
        self.value(store.begin('RUN-PRIVATE',request()))
        self.value(store.save_intent('RUN-PRIVATE','STEP-PRIVATE',intent()))
        path = self.path.parent / 'public.json'
        self.value(Exchange(self.path).export_research(path))
        self.assertNotIn('RUN-PRIVATE',path.read_text())
        self.assertNotIn('synthetic query',path.read_text())
        backup = self.path.parent / 'backup.sqlite3'; restored = self.path.parent / 'restored.sqlite3'
        summary = self.value(backup_local(self.path,backup))
        self.assertEqual(summary['counts']['research_runs'],1)
        self.value(restore_local(backup,restored))
        self.assertEqual(self.value(ResearchRuntimeStore(restored).inspect_run('RUN-PRIVATE')),
                         self.value(store.inspect_run('RUN-PRIVATE')))

    def test_invalid_request_or_missing_run_creates_no_intent(self):
        from records.runtime import ResearchRuntimeStore
        store = ResearchRuntimeStore(self.path)
        for patch in ({'notes':'private'},{'limits':{'total':-1}}, {'deadline':'tomorrow'}):
            self.assertFalse(store.begin('bad',request() | patch)['ok'])
        self.assertFalse(store.save_intent('missing','step',intent())['ok'])
        self.assertFalse(store.inspect_run('missing')['ok'])
        self.value(store.begin('RUN-1',request()))
        self.assertFalse(store.inspect_run('RUN-1', limit=0)['ok'])

    def test_corrupted_runtime_is_not_a_valid_backup(self):
        from contextlib import closing
        from records.runtime import ResearchRuntimeStore
        store = ResearchRuntimeStore(self.path)
        self.value(store.begin('RUN-1',request()))
        with closing(store.db.connect()) as conn:
            conn.execute("UPDATE research_runs SET request_hash='invalid'")
        target = self.path.parent / 'invalid.sqlite3'
        self.assertFalse(backup_local(self.path,target)['ok'])
        self.assertFalse(target.exists())
