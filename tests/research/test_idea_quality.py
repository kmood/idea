import unittest
import tempfile
from pathlib import Path


class IdeaLibraryQualityTests(unittest.TestCase):
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
