"""Verify a copied base without the original checkout or local Linear binding."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class TemplateCopyTests(unittest.TestCase):
    def test_skill_names_descriptions_and_resources(self):
        entries = sorted(ROOT.glob("*/SKILL.md"))
        self.assertEqual(len(entries), 15)
        for entry in entries:
            text = entry.read_text()
            self.assertTrue(text.startswith("---\n"), str(entry))
            header = text.split("---", 2)[1]
            self.assertRegex(header, r"(?m)^name: " + re.escape(entry.parent.name) + r"$")
            self.assertRegex(header, r"(?m)^description: \S.+$")
        resources = ["grilling/references/upstream.md", "grilling/evals/evals.json",
                     "empirical-prompt-tuning/scripts/ept_score.py",
                     "empirical-prompt-tuning/references/example-run.md",
                     "empirical-prompt-tuning/references/manual-scoring.md",
                     "docs/linear.md", "templates/linear-issue.md"]
        for resource in resources:
            self.assertTrue((ROOT / resource).is_file(), resource)

    def test_copy_is_self_contained_and_requires_new_project_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "new project"
            shutil.copytree(ROOT, target, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", ".linear.json", ".env*", ".linear_token", "__pycache__", "*.pyc"))
            self.assertFalse((target / ".linear.json").exists())
            check = subprocess.run(["bash", str(target / "scripts/sync-skills.sh"), "--check"], cwd=folder, capture_output=True, text=True, timeout=15)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            for skill in (target / ".agents/skills").iterdir():
                self.assertEqual(skill.resolve().parent, target.resolve())
            help_result = subprocess.run(["bash", str(target / "scripts/linear"), "--help"], cwd=folder, capture_output=True, text=True, timeout=15)
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            unconfigured = subprocess.run(["bash", str(target / "scripts/linear"), "list"], cwd=folder, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(unconfigured.returncode, 0)
            self.assertIn("未設定", unconfigured.stderr)


if __name__ == "__main__":
    unittest.main()
