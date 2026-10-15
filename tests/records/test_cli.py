import json
import os
import subprocess
import sys
from test_source import StoreCase, source
from test_evidence import evidence, idea


class CliTests(StoreCase):
    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, '-m', 'records', '--db', str(self.path), *args], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0 if success else 2, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def request(self, request, scope='research', success=True):
        path = self.path.parent/'request.json'
        path.write_text(json.dumps(request), encoding='utf-8')
        return self.run_cli('request', '--scope', scope, '--input', str(path), success=success)

    def test_real_process_workflow(self):
        self.run_cli('init')
        for i, record in enumerate((source(), evidence(), idea())):
            self.request(dict(action='createResearch', record=record, operationId=str(i)))
        self.request(dict(action='setPersonalState', id='IDEA-TEST', expectedRevision=None, patch={'notes': 'PRIVATE-SENTINEL', 'favorite': True}, operationId='p'), scope='personal')
        self.request(dict(action='patchResearch', id='EV-TEST', expectedRevision=1, patch={'claim': '更正'}, reason='反证', operationId='fix'))
        output = self.path.parent/'public.json'
        self.run_cli('export', '--output', str(output))
        self.assertNotIn('PRIVATE-SENTINEL', output.read_text())
        backup = self.path.parent/'backup.sqlite3'
        self.run_cli('backup', '--output', str(backup))
        restored = self.path.parent/'restored.sqlite3'
        self.run_cli('restore', '--input', str(backup), '--output', str(restored))
        self.path = restored
        result = self.request(dict(action='readRecord', id='IDEA-TEST'), scope='personal')
        self.assertEqual(result['value']['notes'], 'PRIVATE-SENTINEL')

    def test_bad_requests_and_wrong_scope_are_structured(self):
        bad = self.request(dict(action='setPersonalState', notes='PRIVATE-SENTINEL'), success=False)
        self.assertNotIn('PRIVATE-SENTINEL', str(bad))
        self.assertEqual(bad['error']['code'], 'SCOPE_VIOLATION')
        path = self.path.parent/'bad.json'; path.write_text('{PRIVATE-SENTINEL')
        result = self.run_cli('request', '--input', str(path), success=False)
        self.assertEqual(result['error']['code'], 'VALIDATION_ERROR')
        self.assertNotIn('PRIVATE-SENTINEL', str(result))
