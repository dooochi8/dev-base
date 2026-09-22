"""Local-only bootstrap behavior and mocked Linear project creation."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import linear_cli as linear

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "project-start/scripts/bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
TEAM = "00000000-0000-4000-8000-000000000001"
PROJECT = "00000000-0000-4000-8000-000000000002"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="project start ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "template"
        self.source.mkdir()
        for relative in [*bootstrap.ROOT_FILES, *(f"docs/{n}" for n in bootstrap.DOCS),
                         "scripts/sync-skills.sh", "templates/linear-issue.md",
                         ".github/PULL_REQUEST_TEMPLATE.md", "dev-base/SKILL.md",
                         "dev-base/agents/openai.yaml", "dev-base/references/example.md"]:
            target = self.source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("content\n")
        self.destination = self.root / "new project"
        self.git_state = patch.object(bootstrap, "source_git", return_value={"head": "a" * 40, "dirty": False})
        self.git_state.start()
        self.addCleanup(self.git_state.stop)

    def run_bootstrap(self, **kwargs):
        return bootstrap.bootstrap(self.source, self.destination, "my-app", "テスト用の目的", **kwargs)

    def test_default_dry_run_has_no_mutation(self):
        result = self.run_bootstrap()
        self.assertFalse(result["applied"])
        self.assertFalse(self.destination.exists())
        self.assertEqual(result["skills"], ["dev-base"])

    def test_copy_keeps_resources_and_projects_both_clients_without_private_state(self):
        for private in (".linear.json", ".linear_token", ".env", ".mcp.json", "unrelated-note.md"):
            (self.source / private).write_text("must not copy")
        (self.source / ".git").mkdir()
        result = self.run_bootstrap(apply=True)
        self.assertTrue(result["applied"])
        for private in (".git", ".linear.json", ".linear_token", ".env", ".mcp.json", "unrelated-note.md"):
            self.assertFalse((self.destination / private).exists())
        self.assertEqual((self.destination / ".agents/skills/dev-base").resolve(), (self.destination / "dev-base").resolve())
        self.assertFalse((self.destination / ".claude/skills/dev-base/agents").exists())
        self.assertEqual((self.destination / ".claude/skills/dev-base/references/example.md").read_text(), "content\n")
        self.assertIn("my-app", (self.destination / "README.md").read_text())
        manifest = json.loads((self.destination / "docs/bootstrap.json").read_text())
        self.assertEqual(manifest["externalSetup"], "not-run")
        self.assertNotIn(str(self.source), json.dumps(manifest))

    def test_existing_directory_even_empty_is_not_overwritten(self):
        self.destination.mkdir()
        with self.assertRaises(bootstrap.BootstrapError):
            self.run_bootstrap(apply=True)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_resume_does_not_duplicate_or_erase_local_work(self):
        self.run_bootstrap(apply=True)
        (self.destination / "README.md").write_text("user edited")
        with self.assertRaises(bootstrap.BootstrapError):
            self.run_bootstrap(apply=True)
        self.assertEqual((self.destination / "README.md").read_text(), "user edited")

    def test_dirty_source_needs_explicit_flag(self):
        bootstrap.source_git.return_value["dirty"] = True
        self.assertTrue(self.run_bootstrap()["source"]["dirty"])
        with self.assertRaises(bootstrap.BootstrapError):
            self.run_bootstrap(apply=True)
        self.assertFalse(self.destination.exists())
        self.assertTrue(self.run_bootstrap(apply=True, allow_dirty=True)["applied"])

    def test_symlink_in_canonical_package_is_rejected_before_creation(self):
        (self.source / "dev-base/leak.md").symlink_to(self.root / "outside")
        with self.assertRaises(bootstrap.BootstrapError):
            self.run_bootstrap(apply=True)
        self.assertFalse(self.destination.exists())

    def test_credentials_inside_selected_packages_fail_closed(self):
        (self.source / "dev-base/.env.production").write_text("private")
        with self.assertRaises(bootstrap.BootstrapError):
            self.run_bootstrap(apply=True)
        self.assertFalse(self.destination.exists())

    def test_nested_repository_and_source_destinations_are_rejected(self):
        self.destination = self.source / "new-project"
        with self.assertRaises(bootstrap.BootstrapError):
            self.run_bootstrap(apply=True)
        other = self.root / "other"
        other.mkdir()
        (other / ".git").write_text("gitdir: elsewhere")
        self.destination = other / "nested"
        with self.assertRaises(bootstrap.BootstrapError):
            self.run_bootstrap(apply=True)

    def test_invalid_names_and_empty_purpose_are_rejected(self):
        for name in ("../escape", "my app", "-flag", ""):
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.bootstrap(self.source, self.destination, name, "purpose", True)
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.bootstrap(self.source, self.destination, "valid", " ", True)

    def test_actual_template_copy_retains_all_skills_and_passes_sync_check(self):
        result = bootstrap.bootstrap(ROOT, self.destination, "sample-app", "隔離テスト", True, True)
        expected = sorted(p.parent.name for p in ROOT.glob("*/SKILL.md"))
        self.assertEqual(result["skills"], expected)
        check = subprocess.run(["bash", str(self.destination / "scripts/sync-skills.sh"), "--check"],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        help_result = subprocess.run(["bash", str(self.destination / "scripts/linear"), "--help"],
                                     capture_output=True, text=True, timeout=10)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("project-create", help_result.stdout)


class ProjectCreateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = {"id": PROJECT, "name": "sample", "url": "https://linear.app/example",
                        "teams": {"nodes": [{"id": TEAM}]}}

    def create(self, confirmed=True, name="sample"):
        return linear.create_project(TEAM, name, confirmed, self.root)

    def pages(self, operation, _field):
        return [{"id": TEAM}] if operation == "teams" else []

    def test_confirmation_binding_and_invalid_input_stop_before_api(self):
        with patch.object(linear, "request") as request, patch.object(linear, "pages") as pages:
            for confirmed, name in ((False, "sample"), (True, " "), (True, "bad\nname")):
                with self.assertRaises(linear.LinearError):
                    self.create(confirmed, name)
            (self.root / ".linear.json").write_text("existing binding")
            with self.assertRaises(linear.LinearError):
                self.create()
            request.assert_not_called()
            pages.assert_not_called()

    def test_unknown_team_and_duplicate_project_do_not_mutate(self):
        with patch.object(linear, "pages", return_value=[]), patch.object(linear, "request") as request:
            with self.assertRaises(linear.LinearError):
                self.create()
            request.assert_not_called()
        with patch.object(linear, "pages", side_effect=[[{"id": TEAM}], [self.project]]), patch.object(linear, "request") as request:
            with self.assertRaises(linear.LinearError):
                self.create(name=" SAMPLE ")
            request.assert_not_called()

    def test_success_reads_back_exact_project_and_does_not_bind(self):
        responses = [{"projectCreate": {"success": True, "project": {"id": PROJECT}}}, {"project": self.project}]
        with patch.object(linear, "pages", side_effect=self.pages), patch.object(linear, "request", side_effect=responses) as request:
            result = self.create()
            self.assertEqual(result["readBack"], self.project)
            self.assertFalse(result["configured"])
            self.assertEqual(request.call_args_list[0].args, ("project_create", {"input": {"name": "sample", "teamIds": [TEAM]}}))
            self.assertEqual(request.call_args_list[1].args, ("project_get", {"id": PROJECT}))
        self.assertFalse((self.root / ".linear.json").exists())

    def test_mismatched_readback_is_not_retried(self):
        for field in ("name", "id", "teams"):
            project = deepcopy(self.project)
            project[field] = {"nodes": []} if field == "teams" else "wrong"
            responses = [{"projectCreate": {"success": True, "project": {"id": PROJECT}}}, {"project": project}]
            with patch.object(linear, "pages", side_effect=self.pages), patch.object(linear, "request", side_effect=responses) as request:
                with self.assertRaises(linear.LinearError):
                    self.create()
                self.assertEqual(request.call_count, 2)

    def test_uncertain_create_is_not_retried(self):
        with patch.object(linear, "pages", side_effect=self.pages), patch.object(linear, "request", side_effect=linear.LinearError("network failure")) as request:
            with self.assertRaises(linear.LinearError):
                self.create()
            self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
