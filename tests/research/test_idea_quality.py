import unittest
import tempfile
from pathlib import Path


class IdeaLibraryQualityTests(unittest.TestCase):
    def test_audit_reports_action_gaps_and_readiness_without_rewriting_library(self):
        from research.idea_quality import validate_idea_library
        root = Path(__file__).resolve().parents[2]
        result = validate_idea_library(root)
        self.assertEqual(len(result['audit']), result['indexedCount'])
        item = next(entry for entry in result['audit'] if entry['id'] == 'IDEA-20261021-011')
        self.assertEqual(item['readinessStatus'], '需补证')
        self.assertIn('explorationCycle', item['missing'])
        self.assertIn('acquisitionPath', item['missing'])
        self.assertEqual(result['validCount'], result['indexedCount'])

    def test_negated_field_mentions_and_declared_status_never_become_actionable(self):
        from research.idea_quality import audit_idea_record
        document = (
            '# IDEA-TEST 否定语境测试\n\n'
            '- 研究状态：需补证；缺少付费买方，已撤出近期行动池。\n'
            '- 服务对象与问题：明确对象和问题。\n'
            '- 可能赚钱方式：可拆成固定范围服务，但缺获客路径、探索周期和投入/退出条件。\n'
            '- 个人匹配：有条件适合。\n'
            '- 未知：付款、成交、上线均未知。\n'
            '- 下一步：核验获客路径与最小交付，没有独立小包证据前维持需补证。\n\n'
            '## 证据与反证\n\n'
            '[原始讨论](https://example.com/post) E1具体需求；已有替代。\n\n'
            '| 时间 | 事件与变化 | 原因/证据 | 执行者 |\n'
            '| --- | --- | --- | --- |\n'
            '| 2026-11-08 | 首次收录 | 测试 | 研究助手 |\n'
        )
        record = {'id': 'IDEA-TEST', 'evidence': 'E1具体需求', 'fit': '有条件适合'}
        audit = audit_idea_record(record, document)
        self.assertEqual(audit['readinessStatus'], '需补证')
        self.assertIn('acquisitionPath', audit['missing'])
        self.assertIn('explorationCycle', audit['missing'])
        self.assertIn('commercialOutcome', audit['missing'])

    def test_index_evidence_recognizes_chinese_adjacent_signal(self):
        from research.idea_quality import validate_idea_library
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ideas').mkdir()
            (root / 'ideas/INDEX.md').write_text(
                '严格校验有效点子 1 / 200\n\n| ID | 机会 | 市场 | 证据与时效 | 个人匹配 | 状态 | 最近核验 |\n'
                '| --- | --- | --- | --- | --- | --- | --- |\n'
                '| [IDEA-TEST](IDEA-TEST.md) | 测试 | 国内 | E3历史采购；付款未知 | 有条件适合 | 待验证 | 2026-10-24 |\n',
                encoding='utf-8')
            (root / 'ideas/IDEA-TEST.md').write_text(
                '# IDEA-TEST 测试\n\n'
                '- 服务对象与问题：明确对象和问题。\n'
                '- 可能赚钱方式：固定范围服务。\n'
                '- 个人匹配：有条件适合。\n'
                '- 未知：付款未知。\n'
                '- 下一步：核验当前需求。\n\n'
                '## 证据与反证\n\n'
                '[原始讨论](https://example.com/post) E3历史采购；已有替代。\n\n'
                '| 时间 | 事件与变化 | 原因/证据 | 执行者 |\n'
                '| --- | --- | --- | --- |\n'
                '| 2026-10-24 | 首次收录 | 测试 | 研究助手 |\n', encoding='utf-8')
            result = validate_idea_library(root)
            self.assertEqual(result['violations'], [])
            self.assertEqual(result['audit'][0]['indexEvidenceLevel'], 'E3')

    def test_current_idea_library_meets_strict_entry_requirements(self):
        from research.idea_quality import validate_idea_library
        root = Path(__file__).resolve().parents[2]
        result = validate_idea_library(root)
        self.assertEqual(result['violations'], [])
        self.assertGreaterEqual(result['validCount'], 20)
        self.assertEqual(result['target'], 200)

    def test_evidence_must_be_e1_to_e3_and_have_a_next_action(self):
        from research.idea_quality import validate_idea_library
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ideas').mkdir()
            (root / 'ideas/INDEX.md').write_text(
                '严格校验有效点子 1 / 200\n\n| ID | 机会 |\n| --- | --- |\n'
                '| [IDEA-TEST](IDEA-TEST.md) | 测试 |\n', encoding='utf-8')
            (root / 'ideas/IDEA-TEST.md').write_text(
                '# IDEA-TEST 测试\n\n'
                '- 服务对象与问题：明确对象和问题。\n'
                '- 可能赚钱方式：固定范围服务。\n\n'
                '## 证据与反证\n\n'
                '[原始讨论](https://example.com/post) E0 趋势。已有替代。\n\n'
                '## 个人匹配与未知\n\n'
                '未知项已列出。\n\n'
                '| 时间 | 事件与变化 | 原因/证据 | 执行者 |\n'
                '| --- | --- | --- | --- |\n'
                '| 2026-10-21 | 首次收录 | 测试 | 研究助手 |\n', encoding='utf-8')
            result = validate_idea_library(root)
            self.assertTrue(any('missing E1-E3 evidence level' in item for item in result['violations']))
            self.assertTrue(any('missing next validation action' in item for item in result['violations']))

    def test_incomplete_idea_is_not_counted_as_valid(self):
        from research.idea_quality import validate_idea_library
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ideas').mkdir()
            (root / 'ideas/INDEX.md').write_text(
                '严格校验有效点子 1 / 200\n\n| ID | 机会 |\n| --- | --- |\n'
                '| [IDEA-TEST](IDEA-TEST.md) | 未完成 |\n', encoding='utf-8')
            (root / 'ideas/IDEA-TEST.md').write_text('# IDEA-TEST 未完成\n', encoding='utf-8')
            result = validate_idea_library(root)
            self.assertEqual(result['validCount'], 0)
            self.assertTrue(any('missing concrete source link' in item for item in result['violations']))


if __name__ == '__main__':
    unittest.main()
