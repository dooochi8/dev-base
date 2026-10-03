"""Test pstack integrity and the real project-copy boundary in isolation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from check_pstack import check

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("pstack_bootstrap", ROOT / "project-start/scripts/bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class PstackIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        package = self.root / "example"
        package.mkdir()
        for name in ("UPSTREAM.md", "LICENSE-pstack", "LICENSE-cursor-team-kit"):
            (package / name).write_text("fixture\n")
        source = package / "UPSTREAM-SKILL.md"
        source.write_text("original\n")
        (package / "SKILL.md").write_text("---\nname: example\ndescription: テスト用の入口。\n---\n\n[手順](UPSTREAM-SKILL.md)\n")
        self.manifest = {
            "commit": "a" * 40, "skills": {"example": "テスト用"},
            "files": [{"path": "example/UPSTREAM-SKILL.md", "source": "skills/example/SKILL.md",
                       "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
        }
        self.save_manifest()

    def save_manifest(self):
        (self.root / "docs/pstack-manifest.json").write_text(json.dumps(self.manifest))

    def test_original_drift_and_missing_references_are_detected(self):
        self.assertEqual(check(self.root), [])
        (self.root / "example/UPSTREAM-SKILL.md").write_text("changed\n")
        self.assertTrue(any("source drift" in problem for problem in check(self.root)))
        (self.root / "example/UPSTREAM-SKILL.md").unlink()
        problems = check(self.root)
        self.assertTrue(any("missing" in problem for problem in problems))
        self.assertTrue(any("broken link" in problem for problem in problems))

    def test_manifest_cannot_read_outside_package(self):
        self.manifest["files"][0]["path"] = "../../outside"
        self.save_manifest()
        self.assertTrue(any("範囲外" in problem for problem in check(self.root)))

    def test_repository_sources_and_entry_points_resolve(self):
        self.assertEqual(check(ROOT), [])

    def test_real_bootstrap_keeps_sources_and_excludes_role_config(self):
        with tempfile.TemporaryDirectory(prefix="pstack copy ") as folder:
            target = Path(folder) / "new app"
            bootstrap.bootstrap(ROOT, target, "pstack-app", "複製確認", apply=True, allow_dirty=True)
            self.assertEqual(check(target), [])
            self.assertFalse((target / ".pstack-models.md").exists())
            self.assertFalse((target / ".linear.json").exists())
            self.assertIn("poteto-mode", (target / "README.md").read_text())
            self.assertTrue((target / ".claude/skills/poteto-mode/references/agents/comment-sicko.md").is_file())
            self.assertFalse((target / ".claude/skills/poteto-mode/scripts/node_modules").exists())
            for name in json.loads((target / "docs/pstack-manifest.json").read_text())["skills"]:
                self.assertEqual((target / ".agents/skills" / name).resolve(), (target / name).resolve())
                self.assertEqual((target / ".claude/skills" / name / "SKILL.md").read_bytes(),
                                 (target / name / "SKILL.md").read_bytes())
            result = subprocess.run(["bash", str(target / "scripts/sync-skills.sh"), "--check"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
