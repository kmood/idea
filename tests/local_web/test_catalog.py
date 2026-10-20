import json
import tempfile
import unittest
from pathlib import Path


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for directory in ('ideas','trends','sources','research'):(self.root/directory).mkdir()
        (self.root/'ideas/INDEX.md').write_text(
            '# 点子\n\n| ID | 机会 | 市场 | 证据与时效 | 个人匹配 | 状态 | 最近核验 |\n'
            '| --- | --- | --- | --- | --- | --- | --- |\n'
            '| [IDEA-1](IDEA-1.md) | 术语检查 | 海外电商 | E2；付费未知 | 有条件适合 | 待验证 | 2026-10-15 |\n',encoding='utf-8')
        (self.root/'ideas/IDEA-1.md').write_text('# IDEA-1 术语检查\n\n<script>alert(1)</script>\n\n- 证据：E2\n',encoding='utf-8')
        (self.root/'trends/INDEX.md').write_text(
            '# 趋势\n\n| ID | 观察 | 来源 | 状态 | 最近核验 |\n| --- | --- | --- | --- | --- |\n'
            '| [TREND-1](TREND-1.md) | 客服质检 | GL03 | E0，尚无购买证据 | 2026-10-15 |\n',encoding='utf-8')
        (self.root/'trends/TREND-1.md').write_text('# TREND-1 客服质检\n',encoding='utf-8')
        (self.root/'sources/INDEX.md').write_text(
            '# 来源\n\n| ID | 网站与入口 | 受众/类型 | 优先观察入口与信号 | 访问实测与限制 | 优先级 |\n'
            '| --- | --- | --- | --- | --- | --- |\n'
            '| CN01 | [V2EX](javascript:alert) | 中文开发者 | 求工具 | 列表可读 | A |\n',encoding='utf-8')
        (self.root/'research/STATE.md').write_text('# 运行状态\n\n- 阶段：集中收集。\n',encoding='utf-8')

    def tearDown(self):self.temp.cleanup()

    def test_catalog_normalizes_three_indexes_without_inventing_unknowns(self):
        from local_web.catalog import load_catalog
        catalog=load_catalog(self.root)
        self.assertEqual(catalog['meta']['counts'],{'source':1,'trend':1,'idea':1})
        idea=next(item for item in catalog['records'] if item['kind']=='idea')
        self.assertEqual((idea['id'],idea['evidence'],idea['status']),('IDEA-1','E2；付费未知','待验证'))
        source=next(item for item in catalog['records'] if item['kind']=='source')
        self.assertIsNone(source['evidence'])
        self.assertIsNone(source['url'])
        self.assertEqual(catalog['meta']['phase'],'集中收集')

    def test_markdown_renderer_escapes_html_and_keeps_safe_links(self):
        from local_web.markdown import render_markdown
        rendered=render_markdown('# 标题\n\n<script>alert(1)</script>\n\n[安全](https://example.com) [危险](javascript:alert(1))')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',rendered)
        self.assertNotIn('<script>',rendered)
        self.assertIn('href="https://example.com"',rendered)
        self.assertNotIn('href="javascript:',rendered)

    def test_app_contract_serves_catalog_document_and_rejects_unknown_paths(self):
        from local_web.app import LocalWebApp
        app=LocalWebApp(self.root)
        status,headers,body=app.dispatch('GET','/api/catalog')
        self.assertEqual((status,headers['Content-Type']),(200,'application/json; charset=utf-8'))
        self.assertEqual(len(json.loads(body)['records']),3)
        status,_,body=app.dispatch('GET','/api/documents/idea/IDEA-1')
        document=json.loads(body)
        self.assertEqual((status,document['id'],document['kind']),(200,'IDEA-1','idea'))
        self.assertNotIn('<script>',document['html'])
        status,_,body=app.dispatch('GET','/api/documents/idea/..')
        self.assertEqual((status,json.loads(body)['error']['code']),(400,'INVALID_PATH'))
        status,_,_=app.dispatch('POST','/api/catalog')
        self.assertEqual(status,405)

    def test_malformed_repository_data_returns_a_bounded_error(self):
        from local_web.app import LocalWebApp
        path=self.root/'ideas/INDEX.md'
        path.write_text(path.read_text().replace('IDEA-1.md','../private.md'),encoding='utf-8')
        status,_,body=LocalWebApp(self.root).dispatch('GET','/api/catalog')
        error=json.loads(body)['error']
        self.assertEqual((status,error['code']),(500,'REPOSITORY_ERROR'))
        self.assertNotIn('private.md',error['message'])
