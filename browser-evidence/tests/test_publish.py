import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/publish.py"
spec = importlib.util.spec_from_file_location("evidence_publish", SCRIPT)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
SHA = "a" * 40
CONFIG = {
    "EVIDENCE_S3_ENDPOINT": "https://account.r2.cloudflarestorage.com",
    "EVIDENCE_S3_BUCKET": "review-evidence",
    "EVIDENCE_PUBLIC_BASE_URL": "https://evidence.example.com",
    "EVIDENCE_KEY_PREFIX": "test-project",
    "EVIDENCE_S3_REGION": "auto",
}


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "assets").mkdir()
        self.video = "assets/1234567890abcdef-0-0.webm"
        content = b"\x1aE\xdf\xa3test-video"
        (self.root / self.video).write_bytes(content)
        self.data = {
            "schemaVersion": 1, "runId": "run-test-1", "headSha": SHA,
            "worktreeDirty": False, "status": "passed", "expectedTests": 1, "runnerErrors": 0,
            "tests": [{"title": "Form -> accepted", "status": "passed", "retry": 0,
                       "assets": [{"file": self.video, "contentType": "video/webm", "size": len(content),
                                   "sha256": hashlib.sha256(content).hexdigest()}]}],
        }
        self.manifest = self.root / "manifest.json"
        self.save()
        self.env = patch.dict(os.environ, CONFIG, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def save(self):
        self.manifest.write_text(json.dumps(self.data))

    def test_dry_run_needs_no_credentials_and_never_uploads_or_comments(self):
        with patch.object(publisher, "upload") as upload, patch.object(publisher, "post_comment") as comment:
            result = publisher.publish(self.manifest, SHA, comment=True)
        self.assertEqual(result["mode"], "dry-run")
        upload.assert_not_called()
        comment.assert_not_called()
        body = (self.root / "pr-body.md").read_text()
        self.assertIn("dry-run", body)
        self.assertIn(f"https://evidence.example.com/test-project/{SHA}/run-test-1/{self.video}", body)

    def test_upload_sends_exact_media_with_sigv4_and_excludes_raw_data(self):
        (self.root / "raw").mkdir()
        (self.root / "raw/trace.zip").write_bytes(b"private trace")
        with patch.dict(os.environ, {"EVIDENCE_S3_ACCESS_KEY_ID": "test-key", "EVIDENCE_S3_SECRET_ACCESS_KEY": "test-secret"}), patch.object(publisher, "upload") as upload, patch.object(publisher, "verify_media_url") as verify:
            result = publisher.publish(self.manifest, SHA, apply=True)
        self.assertEqual(result["mode"], "published")
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(verify.call_count, 1)
        request = upload.call_args.args[0]
        self.assertIn(f"/review-evidence/test-project/{SHA}/run-test-1/assets/", request.full_url)
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.data, (self.root / self.video).read_bytes())
        self.assertIn("AWS4-HMAC-SHA256 Credential=test-key/", request.get_header("Authorization"))
        self.assertNotIn("test-secret", (self.root / "publish.json").read_text())

    def test_failed_put_does_not_create_success_receipt(self):
        with patch.dict(os.environ, {"EVIDENCE_S3_ACCESS_KEY_ID": "test-key", "EVIDENCE_S3_SECRET_ACCESS_KEY": "test-secret"}), patch.object(publisher, "upload", side_effect=publisher.EvidenceError("failed")), patch.object(publisher, "post_comment") as comment:
            with self.assertRaises(publisher.EvidenceError):
                publisher.publish(self.manifest, SHA, apply=True)
        self.assertFalse((self.root / "publish.json").exists())
        comment.assert_not_called()

    def test_unreadable_public_url_does_not_claim_published_success(self):
        with patch.dict(os.environ, {"EVIDENCE_S3_ACCESS_KEY_ID": "test-key", "EVIDENCE_S3_SECRET_ACCESS_KEY": "test-secret"}), patch.object(publisher, "upload"), patch.object(publisher, "verify_media_url", side_effect=publisher.EvidenceError("unreadable")):
            with self.assertRaisesRegex(publisher.EvidenceError, "unreadable"):
                publisher.publish(self.manifest, SHA, apply=True)
        self.assertFalse((self.root / "publish.json").exists())

    def test_wrong_sha_dirty_source_and_modified_media_are_rejected(self):
        with self.assertRaisesRegex(publisher.EvidenceError, "head SHA"):
            publisher.load_manifest(self.manifest, "b" * 40)
        self.data["worktreeDirty"] = True
        self.save()
        with self.assertRaisesRegex(publisher.EvidenceError, "clean source"):
            publisher.load_manifest(self.manifest, SHA)
        self.data["worktreeDirty"] = False
        self.save()
        (self.root / self.video).write_bytes(b"corrupted")
        with self.assertRaisesRegex(publisher.EvidenceError, "checksum"):
            publisher.load_manifest(self.manifest, SHA)

    def test_traversal_symlink_and_non_media_are_rejected(self):
        asset = self.data["tests"][0]["assets"][0]
        for filename in ["../private.webm", "assets/token.json", "assets/1234567890abcdef-0-0.html"]:
            asset["file"] = filename
            self.save()
            with self.subTest(filename=filename), self.assertRaises(publisher.EvidenceError):
                publisher.load_manifest(self.manifest, SHA)
        asset["file"] = self.video
        self.save()
        media = self.root / self.video
        media.unlink()
        media.symlink_to(self.manifest)
        with self.assertRaisesRegex(publisher.EvidenceError, "symlinks"):
            publisher.load_manifest(self.manifest, SHA)

    def test_incomplete_or_skipped_tests_cannot_claim_success(self):
        self.data["expectedTests"] = 2
        self.save()
        with self.assertRaisesRegex(publisher.EvidenceError, "every scenario"):
            publisher.load_manifest(self.manifest, SHA)
        self.data["expectedTests"] = 1
        self.data["tests"][0]["status"] = "skipped"
        self.save()
        with self.assertRaises(publisher.EvidenceError):
            publisher.load_manifest(self.manifest, SHA)

    def test_head_changed_before_upload_blocks_all_external_writes(self):
        pr = {"state": "open", "head": {"sha": "b" * 40, "repo": {"full_name": "owner/repo"}}}
        with patch.dict(os.environ, {"EVIDENCE_S3_ACCESS_KEY_ID": "test-key", "EVIDENCE_S3_SECRET_ACCESS_KEY": "test-secret"}), patch.object(publisher, "gh_json", return_value=pr), patch.object(publisher, "upload") as upload:
            with self.assertRaisesRegex(publisher.EvidenceError, "does not match"):
                publisher.publish(self.manifest, SHA, apply=True, repo="owner/repo", pr_number=1, comment=True)
        upload.assert_not_called()

    def test_comment_updates_only_the_current_actor_marker_and_reads_back(self):
        body = publisher.MARKER + "\nEvidence"
        pr = {"state": "open", "head": {"sha": SHA, "repo": {"full_name": "owner/repo"}}}
        comments = [[{"id": 1, "user": {"login": "someone"}, "body": body},
                     {"id": 2, "user": {"login": "github-actions[bot]"}, "body": body}]]
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}), patch.object(publisher, "gh_json", side_effect=[pr, comments, {"id": 2}, {"body": body, "html_url": "https://github.com/owner/repo/pull/1#comment"}]) as gh:
            url = publisher.post_comment("owner/repo", 1, SHA, body)
        self.assertIn("#comment", url)
        self.assertEqual(gh.call_args_list[2].args[0][:3], ["--method", "PATCH", "repos/owner/repo/issues/comments/2"])

    def test_private_urls_and_storage_redirects_are_rejected(self):
        for value in ["http://example.com", "https://key:secret@example.com", "https://example.com?token=secret"]:
            with self.assertRaises(publisher.EvidenceError):
                publisher.https_url(value, "endpoint")
        with self.assertRaisesRegex(publisher.EvidenceError, "redirect"):
            publisher.NoRedirect().redirect_request(None, None, 307, "redirect", {}, "https://other.example.com")


if __name__ == "__main__":
    unittest.main()
