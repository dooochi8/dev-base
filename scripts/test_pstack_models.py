"""禁止モデルがサブエージェントの既定値に混ざらないことを検査する。"""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path(__file__).with_name("check-pstack-models")
loader = importlib.machinery.SourceFileLoader("check_pstack_models", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
checker = importlib.util.module_from_spec(spec)
loader.exec_module(checker)


class PstackModelGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        self.write_manifest()

    def write_manifest(self, pinned=()):
        manifest = {"files": [{"path": path} for path in pinned], "licenseFiles": []}
        (self.root / "docs/pstack-manifest.json").write_text(json.dumps(manifest))

    def test_entry_points_require_a_failed_launch(self):
        for relative in (
            "AGENTS.md",
            "poteto-mode/SKILL.md",
            "poteto-mode/references/runtime.md",
            "setup-pstack/SKILL.md",
        ):
            text = (ROOT / relative).read_text()
            self.assertIn("失敗として止める", text)
            self.assertIn("codex:gpt", text)
            self.assertIn("scripts/check-pstack-models", text)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("起動は失敗", readme)
        self.assertIn("scripts/check-pstack-models", readme)

    def test_repository_keeps_pinned_upstream_out_of_scope(self):
        upstream = (ROOT / "poteto-mode/UPSTREAM-SKILL.md").read_text()
        self.assertIn("feature, refactoring: `opus`", upstream)
        self.assertEqual(checker.check(ROOT), [])

    def test_local_role_default_fails_and_pinned_copy_does_not(self):
        pinned = "example/UPSTREAM-SKILL.md"
        self.write_manifest([pinned])
        for relative in (pinned, f".claude/skills/{pinned}"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("- feature, refactoring: `opus`\n- bug-fix: fable\n")
        self.assertEqual(checker.check(self.root), [])
        (self.root / "docs/roles.md").write_text("architect runners: `opus`, `fable`, `sonnet`\n")
        problems = checker.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("docs/roles.md:1", problems[0])
        self.assertIn("opus", problems[0])

    def test_sheet_rejects_forbidden_names_and_allows_inheritance(self):
        allowed = self.root / ".pstack-models.md"
        allowed.write_text("feature, refactoring: inherit-parent\ndefault effort: session\nfeature: grok-4.7\n")
        self.assertEqual(checker.check(self.root), [])
        samples = [
            "opus",
            "Sonnet",
            "haiku",
            "fable",
            "claude-opus-4-5",
            "gpt-6-astra",
            "codex:gpt-6",
            "gemini-2.5-pro",
            "anthropic/claude-sonnet-5-5",
            "openai/gpt-6-sol",
            "# comment keeps opus out",
        ]
        for sample in samples:
            allowed.write_text(f"feature, refactoring: inherit-parent\n{sample}\n")
            problems = checker.check(self.root)
            self.assertTrue(problems, sample)
            self.assertIn(".pstack-models.md", problems[0])

    def test_prose_and_session_inheritance_are_not_defaults(self):
        prose = (
            "サブエージェントの model 引数に opus、sonnet、haiku、fable、claude を渡したら失敗する。"
            "GPT族は gpt- で始まる識別子と codex:gpt。Gemini族は gemini で始まる識別子。\n"
            "既定は `feature, refactoring: inherit-parent` と `default effort: session`。\n"
            "リポジトリ名は pstack-claude。確認済みなら grok-4.7 を書いてよい。\n"
        )
        (self.root / "AGENTS.md").write_text(prose)
        (self.root / "settings.toml").write_text('model = "grok-4.7"\n')
        self.assertEqual(checker.check(self.root), [])

    def test_model_assignment_list_and_table_fail(self):
        (self.root / "settings.toml").write_text('model = "claude-opus-4-5"\n')
        (self.root / "panel.yml").write_text("model: gemini-2.5-flash\n")
        (self.root / "models.json").write_text('{"feature": "haiku"}\n')
        (self.root / "aliases.md").write_text("pi models: opus=<provider/id>, sonnet=<provider/id>\n- fable\n| gpt-6-astra |\n")
        problems = checker.check(self.root)
        joined = "\n".join(problems)
        for needle in ("settings.toml", "panel.yml", "models.json", "aliases.md", "claude-opus-4-5", "gemini-2.5-flash", "haiku", "opus", "fable", "gpt-6-astra"):
            self.assertIn(needle, joined)

    def test_cli_fails_on_a_sheet_and_passes_when_clean(self):
        failed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root)],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(failed.returncode, 0, failed.stderr)
        (self.root / ".pstack-models.md").write_text("bug-fix: fable\n")
        failed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root)],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(failed.returncode, 1)
        self.assertIn("fable", failed.stderr)
        self.assertIn(".pstack-models.md", failed.stderr)


if __name__ == "__main__":
    unittest.main()
