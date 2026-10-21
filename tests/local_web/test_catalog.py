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
        self.assertEqual(catalog['meta']['filters']['ideaResearchStatus'],['待验证'])
        self.assertEqual(catalog['meta']['filters']['ideaFit'],['有条件适合'])
        self.assertEqual(catalog['meta']['filters']['sourceAccessStatus'],['可读'])
        self.assertEqual(catalog['meta']['sourceMetrics'],{'entryCount':1,'hostnameCount':0})
        idea=next(item for item in catalog['records'] if item['kind']=='idea')
        self.assertEqual((idea['id'],idea['evidence'],idea['status'],idea['researchStatus']),('IDEA-1','E2；付费未知','待验证','待验证'))
        self.assertEqual((idea['fit'],idea['evidenceLevel']),('有条件适合','E2'))
        source=next(item for item in catalog['records'] if item['kind']=='source')
        self.assertEqual((source['evidence'],source['url'],source['accessStatus']),(None,None,'可读'))
        self.assertEqual(catalog['meta']['phase'],'集中收集')

    def test_catalog_counts_real_statuses_and_hostnames_without_merging_entries(self):
        (self.root/'ideas/INDEX.md').write_text(
            '# 点子\n\n| ID | 机会 | 市场 | 证据与时效 | 个人匹配 | 状态 | 最近核验 |\n'
            '| --- | --- | --- | --- | --- | --- | --- |\n'
            '| [IDEA-1](IDEA-1.md) | 待验证方向 | 国内 | E1 | 有条件适合 | 待验证 | 2026-10-15 |\n'
            '| [IDEA-2](IDEA-2.md) | 候选方向 | 海外 | E3 | 较适合 | 候选 | 2026-10-16 |\n'
            '| [IDEA-3](IDEA-3.md) | 搁置方向 | 国内 | E1 | 暂不适合 | 搁置 | 2026-10-17 |\n',encoding='utf-8')
        for name in ('IDEA-2.md','IDEA-3.md'):
            (self.root/'ideas'/name).write_text('# '+name[:-3]+' 方向\n',encoding='utf-8')
        (self.root/'sources/INDEX.md').write_text(
            '# 来源\n\n| ID | 网站与入口 | 受众/类型 | 优先观察入口与信号 | 访问实测与限制 | 优先级 |\n'
            '| --- | --- | --- | --- | --- | --- |\n'
            '| CN01 | [站点一](https://example.com/a) | 中文 | 求工具 | 入口和具体讨论可读 | A |\n'
            '| GL01 | [站点二](https://example.com/b) | 英文 | 求工具 | 入口受限 | B |\n',encoding='utf-8')
        from local_web.catalog import load_catalog
        catalog=load_catalog(self.root)
        self.assertEqual(catalog['meta']['statusCounts']['idea'],{'候选':1,'搁置':1,'待验证':1})
        self.assertEqual(catalog['meta']['statusCounts']['source'],{'可读':1,'受限':1})
        self.assertEqual(catalog['meta']['selectedCount'],0)
        self.assertEqual(catalog['meta']['filters']['sourceAccessStatus'],['可读','受限'])
        self.assertEqual(catalog['meta']['sourceMetrics'],{'entryCount':2,'hostnameCount':1})
        records={record['id']:record for record in catalog['records']}
        self.assertEqual(records['IDEA-2']['evidenceNote'],'存在采购/报价/付款信号，具体类型见详情。')
        self.assertEqual(records['CN01']['accessStatus'],'可读')
        self.assertEqual(records['GL01']['accessStatus'],'受限')

    def test_markdown_renderer_escapes_html_and_keeps_safe_links(self):
        from local_web.markdown import render_markdown
        rendered=render_markdown('# 标题\n\n<script>alert(1)</script>\n\n[安全](https://example.com) [危险](javascript:alert(1))')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',rendered)
        self.assertNotIn('<script>',rendered)
        self.assertIn('href="https://example.com"',rendered)
        self.assertNotIn('href="javascript:',rendered)

    def test_markdown_renderer_keeps_ordered_evidence_items_and_inline_code(self):
        from local_web.markdown import render_markdown
        rendered=render_markdown('## 证据\n\n1. 第一条，见 `EV-1`。\n2. 第二条，[来源](https://example.com)。\n\n- 反证\n\n| 字段 | 值 |\n| --- | --- |\n| API | `orders` |')
        self.assertIn('<ol><li>第一条，见 <code>EV-1</code>。</li><li>第二条，<a href="https://example.com" rel="noreferrer">来源</a>。</li></ol>',rendered)
        self.assertIn('<ul><li>反证</li></ul>',rendered)
        self.assertIn('<td><code>orders</code></td>',rendered)

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

    def test_static_page_exposes_distinct_status_filters_and_metrics(self):
        from local_web.app import LocalWebApp
        status,_,body=LocalWebApp(self.root).dispatch('GET','/')
        page=body.decode('utf-8')
        self.assertEqual(status,200)
        for marker in ('source-hostname-count','idea-status-counts','research-status','idea-fit','access-status','selected-count','advanced-filters','compare-panel','compare-list','refresh','check-consistency','refresh-status'):
            self.assertIn(marker,page)
        self.assertIn('value="idea" checked',page)

    def test_malformed_repository_data_returns_a_bounded_error(self):
        from local_web.app import LocalWebApp
        path=self.root/'ideas/INDEX.md'
        path.write_text(path.read_text().replace('IDEA-1.md','../private.md'),encoding='utf-8')
        status,_,body=LocalWebApp(self.root).dispatch('GET','/api/catalog')
        error=json.loads(body)['error']
        self.assertEqual((status,error['code']),(500,'REPOSITORY_ERROR'))
        self.assertNotIn('private.md',error['message'])

    def test_consistency_endpoint_reports_missing_public_documents(self):
        from local_web.app import LocalWebApp
        status,_,body=LocalWebApp(self.root).dispatch('GET','/api/consistency')
        result=json.loads(body)
        self.assertEqual((status,result['ok'],result['errors']),(200,True,[]))
        (self.root/'ideas/IDEA-1.md').unlink()
        status,_,body=LocalWebApp(self.root).dispatch('GET','/api/consistency')
        result=json.loads(body)
        self.assertEqual(status,200)
        self.assertFalse(result['ok'])
        self.assertIn('IDEA-1 正文不存在',result['errors'])
