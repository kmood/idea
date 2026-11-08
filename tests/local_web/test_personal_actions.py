import json
import tempfile
import unittest
from pathlib import Path


class PersonalActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in ('ideas', 'trends', 'sources', 'research'):
            (self.root / directory).mkdir()
        (self.root / 'ideas/INDEX.md').write_text(
            '# 点子\n\n| ID | 机会 | 市场 | 证据与时效 | 个人匹配 | 状态 | 最近核验 |\n'
            '| --- | --- | --- | --- | --- | --- | --- |\n'
            '| [IDEA-1](IDEA-1.md) | 术语检查 | 国内 | E1 | 未知 | 待验证 | 2026-10-15 |\n',
            encoding='utf-8')
        (self.root / 'ideas/IDEA-1.md').write_text('# IDEA-1 术语检查\n', encoding='utf-8')
        (self.root / 'trends/INDEX.md').write_text('# 趋势\n', encoding='utf-8')
        (self.root / 'sources/INDEX.md').write_text('# 来源\n', encoding='utf-8')
        (self.root / 'research/STATE.md').write_text('# 运行状态\n', encoding='utf-8')
        self.db = self.root / '.local' / 'records.sqlite3'
        from records.service import ResearchStore
        self.store = ResearchStore(self.db)
        self.value(self.store.create_research({
            'id': 'IDEA-1', 'kind': 'Source', 'name': '合成记录',
            'url': 'https://example.com', 'audience': ['测试'], 'languages': ['zh'],
            'accessStatus': 'readable', 'lastAttempt': None, 'lastSuccess': None,
        }, 'create'))

    def tearDown(self):
        self.temp.cleanup()

    def value(self, result):
        self.assertTrue(result['ok'], result)
        return result['value']

    def test_mark_not_applicable_writes_private_ignored_state_and_is_idempotent(self):
        from local_web.app import LocalWebApp
        app = LocalWebApp(self.root, self.db)
        payload = json.dumps({'id': 'IDEA-1', 'expectedRevision': None,
                              'operationId': 'mark-idea-1-not-applicable'}).encode()
        status, _, body = app.dispatch('POST', '/api/personal-state', payload)
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(result['ok'])
        self.assertTrue(result['value']['ignored'])
        status, _, body = app.dispatch('GET', '/api/personal-state/IDEA-1')
        result = json.loads(body)
        self.assertEqual((status, result['value']['ignored']), (200, True))
        status, _, body = app.dispatch('GET', '/api/personal-states')
        result = json.loads(body)
        self.assertEqual((status, result['value']), (200, ['IDEA-1']))
        self.assertNotIn('notes', result['value'])
        status, _, body = app.dispatch('POST', '/api/personal-state', payload)
        self.assertEqual((status, json.loads(body)['value']['revision']), (200, 1))

    def test_static_page_has_not_applicable_action_copy(self):
        from local_web.app import LocalWebApp
        status, _, body = LocalWebApp(self.root, self.db).dispatch('GET', '/')
        self.assertEqual(status, 200)
        page = body.decode('utf-8')
        self.assertIn('本人不适用', page)
