"""Safety and behavior checks with no requests to Linear."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import linear_cli as cli

TEAM = "00000000-0000-4000-8000-000000000001"
PROJECT = "00000000-0000-4000-8000-000000000002"
CONFIG = {"teamId": TEAM, "projectId": PROJECT}
ISSUE = {"id": "issue-1", "identifier": "TEST-1", "title": "existing",
         "team": {"id": TEAM}, "project": {"id": PROJECT},
         "state": {"id": "todo", "type": "unstarted"}, "labels": {"nodes": []}}


class LinearTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".linear.json").write_text(json.dumps(CONFIG))

    def execute(self, args):
        return cli.execute(cli.parser().parse_args(args), self.root)

    def test_delete_and_arbitrary_api_rejected_before_credentials(self):
        for action in ("delete", "remove", "purge", "issueDelete"):
            with patch.object(cli, "load_token") as token, patch.object(cli.sys, "argv", ["linear", action]), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(), 64)
                token.assert_not_called()
        with patch.object(cli, "load_token") as token:
            with self.assertRaises(cli.LinearError):
                cli.request("mutation { issueDelete(id: 1) }", {})
            token.assert_not_called()

    def test_unconfigured_copy_cannot_contact_api(self):
        (self.root / ".linear.json").unlink()
        with patch.object(cli, "request") as api:
            with self.assertRaises(cli.LinearError):
                self.execute(["create", "--title", "test"])
            api.assert_not_called()

    def test_init_checks_scope_and_never_overwrites(self):
        with patch.object(cli, "request") as api:
            with self.assertRaises(cli.LinearError):
                cli.initialize(TEAM, PROJECT, self.root)
            api.assert_not_called()
        (self.root / ".linear.json").unlink()
        with patch.object(cli, "request", return_value={"team": {"id": TEAM}, "project": {"id": PROJECT, "teams": {"nodes": []}}}):
            with self.assertRaises(cli.LinearError):
                cli.initialize(TEAM, PROJECT, self.root)
        self.assertFalse((self.root / ".linear.json").exists())
        with patch.object(cli, "verify_scope", return_value={}):
            cli.initialize(TEAM, PROJECT, self.root)
        self.assertEqual(json.loads((self.root / ".linear.json").read_text()), CONFIG)

    def test_cross_project_and_cross_team_block_all_targeted_writes(self):
        for field in ("project", "team"):
            wrong = deepcopy(ISSUE)
            wrong[field]["id"] = "outside"
            for args in (["update", "--id", "TEST-1", "--title", "new"],
                         ["comment", "--id", "TEST-1", "--body", "test"],
                         ["cancel", "--id", "TEST-1", "--reason", "test"]):
                with patch.object(cli, "request", return_value={"issue": wrong}) as api:
                    with self.assertRaises(cli.LinearError):
                        self.execute(args)
                    self.assertEqual([c.args[0] for c in api.call_args_list], ["get"])

    def test_all_pages_and_archived_are_included(self):
        def api(operation, variables):
            self.assertEqual(operation, "list")
            self.assertTrue(variables["archived"])
            self.assertEqual(variables["filter"]["project"]["id"]["eq"], PROJECT)
            second = variables["after"] == "cursor-1"
            return {"issues": {"nodes": [{"id": "b" if second else "a"}],
                               "pageInfo": {"hasNextPage": not second, "endCursor": "cursor-1"}}}
        with patch.object(cli, "verify_scope"), patch.object(cli, "request", side_effect=api):
            result = self.execute(["list"])
            self.assertEqual(result["count"], 2)
            self.assertFalse(result["hasNextPage"])

    def test_pagination_failure_is_not_partial_success(self):
        page = {"issues": {"nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": "same"}}}
        with patch.object(cli, "request", return_value=page):
            with self.assertRaises(cli.LinearError):
                cli.pages("list", "issues")

    def test_update_reads_before_and_after(self):
        updated = dict(ISSUE, title="new")
        with patch.object(cli, "request", side_effect=[{"issue": ISSUE}, {"issueUpdate": {"success": True, "issue": {"id": ISSUE["id"]}}}, {"issue": updated}]) as api:
            result = self.execute(["update", "--id", "TEST-1", "--title", "new"])
            self.assertEqual(result["readBack"]["title"], "new")
            self.assertEqual([c.args[0] for c in api.call_args_list], ["get", "update", "get"])

    def test_readback_mismatch_does_not_retry(self):
        with patch.object(cli, "request", side_effect=[{"issueUpdate": {"success": True, "issue": {"id": ISSUE["id"]}}}, {"issue": ISSUE}]) as api:
            with self.assertRaises(cli.LinearError):
                cli.write_issue("update", {"title": "new"}, CONFIG, ISSUE["id"])
            self.assertEqual(api.call_count, 2)

    def test_create_fixes_scope_and_blocks_external_parent(self):
        created = dict(ISSUE, title="new")
        with patch.object(cli, "verify_scope"), patch.object(cli, "lookup_state", return_value={"id": "todo", "type": "unstarted"}), patch.object(cli, "request", side_effect=[{"issueCreate": {"success": True, "issue": {"id": "issue-1"}}}, {"issue": created}]) as api:
            self.execute(["create", "--title", "new"])
            fields = api.call_args_list[0].args[1]["input"]
            self.assertEqual(fields["teamId"], TEAM)
            self.assertEqual(fields["projectId"], PROJECT)
        wrong = dict(ISSUE, project=None)
        with patch.object(cli, "verify_scope"), patch.object(cli, "lookup_state", return_value={"id": "todo", "type": "unstarted"}), patch.object(cli, "request", return_value={"issue": wrong}) as api:
            with self.assertRaises(cli.LinearError):
                self.execute(["create", "--title", "new", "--parent", "OTHER-1"])
            self.assertEqual([c.args[0] for c in api.call_args_list], ["get"])

    def test_cancel_requires_reason_and_comment_readback_before_state(self):
        with patch.object(cli, "request") as api:
            with self.assertRaises(cli.LinearError):
                self.execute(["cancel", "--id", "TEST-1", "--reason", " "])
            api.assert_not_called()
        with patch.object(cli, "get_issue", return_value=ISSUE), patch.object(cli, "lookup_state", return_value={"id": "cancel", "type": "canceled"}), patch.object(cli, "add_comment", side_effect=cli.LinearError("unconfirmed")), patch.object(cli, "write_issue") as mutation:
            with self.assertRaises(cli.LinearError):
                self.execute(["cancel", "--id", "TEST-1", "--reason", "test"])
            mutation.assert_not_called()
        canceled = dict(ISSUE, state={"id": "cancel", "type": "canceled"})
        with patch.object(cli, "get_issue", return_value=canceled), patch.object(cli, "lookup_state", return_value=canceled["state"]), patch.object(cli, "add_comment") as comment:
            self.assertTrue(self.execute(["cancel", "--id", "TEST-1", "--reason", "test"])["alreadyCanceled"])
            comment.assert_not_called()

    def test_comment_reads_new_comment_id(self):
        comment = {"id": "comment-1", "body": "actual", "issue": {"id": ISSUE["id"]}}
        with patch.object(cli, "get_issue", return_value=ISSUE), patch.object(cli, "request", side_effect=[{"commentCreate": {"success": True, "comment": {"id": "comment-1"}}}, {"comment": comment}]) as api:
            self.assertEqual(cli.add_comment("TEST-1", "actual", CONFIG)["commentReadBack"], comment)
            self.assertEqual(api.call_args_list[1].args, ("read_comment", {"id": "comment-1"}))

    def test_duplicate_requires_reason_and_uses_its_actual_state_type(self):
        state = {"id": "duplicate", "type": "duplicate"}
        with patch.object(cli, "get_issue", return_value=ISSUE), patch.object(cli, "lookup_state", return_value=state), patch.object(cli, "add_comment", return_value={}) as comment, patch.object(cli, "write_issue", return_value={"success": True}) as mutation:
            self.execute(["cancel", "--id", "TEST-1", "--state", "Duplicate", "--reason", "TEST-2と重複"])
            comment.assert_called_once()
            self.assertEqual(mutation.call_args.args[1], {"stateId": "duplicate"})
        with patch.object(cli, "get_issue", return_value=ISSUE), patch.object(cli, "lookup_state", return_value=state), patch.object(cli, "write_issue") as mutation:
            with self.assertRaises(cli.LinearError):
                self.execute(["update", "--id", "TEST-1", "--state", "Duplicate"])
            mutation.assert_not_called()

    def test_markdown_file_is_read_literally(self):
        path = self.root / "body.md"
        body = "# Test\n\n`literal` $(not-a-command)\n"
        path.write_text(body)
        args = cli.parser().parse_args(["comment", "--id", "TEST-1", "--body-file", str(path)])
        self.assertEqual(cli.text_value(args, "body"), body)

    def test_wrapper_works_from_another_directory(self):
        result = subprocess.run(["bash", str(cli.ROOT / "scripts/linear"), "--help"], cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("discover", result.stdout)


if __name__ == "__main__":
    unittest.main()
