import unittest
import tempfile
from pathlib import Path


class IdeaLibraryQualityTests(unittest.TestCase):
    def test_current_idea_library_meets_strict_entry_requirements(self):
        from research.idea_quality import validate_idea_library
        root=Path(__file__).resolve().parents[2]
        result=validate_idea_library(root)
        self.assertEqual(result['violations'],[])
        self.assertGreaterEqual(result['validCount'],20)
        self.assertEqual(result['target'],100)

    def test_incomplete_idea_is_not_counted_as_valid(self):
        from research.idea_quality import validate_idea_library
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'ideas').mkdir()
            (root/'ideas/INDEX.md').write_text(
                '严格校验有效点子 1 / 100\n\n| ID | 机会 |\n| --- | --- |\n'
                '| [IDEA-TEST](IDEA-TEST.md) | 未完成 |\n',encoding='utf-8')
            (root/'ideas/IDEA-TEST.md').write_text('# IDEA-TEST 未完成\n',encoding='utf-8')
            result=validate_idea_library(root)
            self.assertEqual(result['validCount'],0)
            self.assertTrue(any('missing concrete source link' in item for item in result['violations']))


if __name__=='__main__':unittest.main()
