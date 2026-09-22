"""Verify a copied base without the original checkout or local Linear binding."""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class TemplateCopyTests(unittest.TestCase):
    def test_skill_names_descriptions_and_resources(self):
        entries = sorted(ROOT.glob("*/SKILL.md"))
        self.assertEqual(len(entries), 20)
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
                     "docs/linear.md", "templates/linear-issue.md",
                     "smart-docs/references/documentation-templates.md",
                     "smart-docs/UPSTREAM.md", "smart-docs/LICENSE",
                     "emil-design-eng/references/upstream.md",
                     "emil-design-eng/UPSTREAM.md", "emil-design-eng/LICENSE",
                     "plan-eng-review/SKILL.md", "plan-design-review/SKILL.md",
                     "project-start/SKILL.md", "project-start/scripts/bootstrap.py",
                     "project-start/references/connections.md"]
        for resource in resources:
            self.assertTrue((ROOT / resource).is_file(), resource)

    def test_smart_docs_package_is_portable(self):
        package = ROOT / "smart-docs"
        for entry in package.rglob("*.md"):
            text = entry.read_text()
            self.assertNotIn("/Users/", text)
            self.assertNotIn("docs/workflows/vault.md", text)
            self.assertNotIn("10_dev/", text)
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                destination = (entry.parent / target.split("#", 1)[0]).resolve()
                self.assertIn(package.resolve(), destination.parents)
                self.assertTrue(destination.is_file(), str(destination))
        license_text = (package / "LICENSE").read_text()
        self.assertIn("Copyright (c) 2025 Sopaco", license_text)
        self.assertIn("MIT License", license_text)
        self.assertFalse((package / "install.sh").exists())
        self.assertIn("`smart-docs`", (ROOT / "README.md").read_text())

    def test_emil_design_eng_preserves_upstream_and_routes_to_it(self):
        package = ROOT / "emil-design-eng"
        source = package / "references/upstream.md"
        manifest = (package / "UPSTREAM.md").read_text()
        expected_hash = re.search(r"SHA256: `([a-f0-9]{64})`", manifest)
        self.assertIsNotNone(expected_hash)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected_hash[1])
        self.assertRegex(manifest, r"Commit: `[a-f0-9]{40}`")
        entry = (package / "SKILL.md").read_text()
        self.assertIn("(references/upstream.md)", entry)
        self.assertIn("prefers-reduced-motion", entry)
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", entry):
            self.assertFalse(target.startswith("/"))
            self.assertTrue((package / target).is_file(), target)
        self.assertIn("Copyright (c) 2026 Emil Kowalski", (package / "LICENSE").read_text())
        self.assertEqual({p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()},
                         {"SKILL.md", "UPSTREAM.md", "LICENSE", "references/upstream.md"})

    def test_plan_review_packages_preserve_verdicts_and_are_portable(self):
        verdicts = {
            "plan-eng-review": ("Ready", "Needs narrowing", "Risky", "Under-specified"),
            "plan-design-review": ("Clear", "Needs simplification", "Missing states", "Confusing"),
        }
        for name, expected in verdicts.items():
            with self.subTest(skill=name):
                package = ROOT / name
                text = (package / "SKILL.md").read_text()
                self.assertNotIn("/Users/", text)
                self.assertNotIn("10_dev/", text)
                for verdict in expected:
                    self.assertIn(verdict, text)
                self.assertEqual({p.name for p in package.iterdir()}, {"SKILL.md"})
                self.assertIn("`" + name + "`", (ROOT / "README.md").read_text())
                self.assertIn(name, (ROOT / "AGENTS.md").read_text())

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
