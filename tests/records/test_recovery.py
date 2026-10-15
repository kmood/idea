import json
import subprocess
import sys
from test_source import StoreCase, source


class RecoveryTests(StoreCase):
    def child(self, body):
        code = 'import os, sys, json\nfrom records.service import ResearchStore\nimport records.service as service\ns = ResearchStore(sys.argv[1])\n' + body
        return subprocess.run([sys.executable, '-c', code, str(self.path)], capture_output=True, timeout=10)

    def test_exit_before_commit_rolls_back_record_history_and_replay(self):
        result = self.child('original = service.save\ndef crash(*args):\n original(*args)\n os._exit(71)\nservice.save = crash\ns.create_research(' + repr(source()) + ', "create")')
        self.assertEqual(result.returncode, 71, result.stderr)
        self.assertEqual(self.store.read_record('CN-TEST')['error']['code'], 'NOT_FOUND')
        self.value(self.store.create_research(source(), 'create'))
        self.assertEqual(len(self.value(self.store.list_history('CN-TEST'))['items']), 1)

    def test_exit_after_commit_replays_original_result(self):
        result = self.child('s.create_research(' + repr(source()) + ', "create")\nos._exit(72)')
        self.assertEqual(result.returncode, 72, result.stderr)
        original = self.value(self.store.read_record('CN-TEST'))['record']
        self.assertEqual(self.value(self.store.create_research(source(), 'create')), original)
        self.assertEqual(len(self.value(self.store.list_history('CN-TEST'))['items']), 1)

    def test_lock_timeout_is_bounded_and_retry_is_safe(self):
        self.store.db.timeout = 0.05
        lock = self.store.db.connect()
        try:
            lock.execute('BEGIN IMMEDIATE')
            result = self.store.create_research(source(), 'create')
            self.assertEqual(result['error']['code'], 'STORAGE_ERROR')
        finally:
            lock.execute('ROLLBACK')
            lock.close()
        self.value(self.store.create_research(source(), 'create'))
