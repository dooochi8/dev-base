#!/usr/bin/env python3
"""Validate browser evidence, upload media to S3/R2, and optionally update a PR comment."""
import argparse
import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

MARKER = "<!-- browser-evidence:report -->"
TYPES = {".webm": "video/webm", ".mp4": "video/mp4", ".png": "image/png"}


class EvidenceError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def https_url(value, name):
    url = urllib.parse.urlsplit(value)
    require(url.scheme == "https" and url.hostname and not url.username and not url.password
            and not url.query and not url.fragment, f"{name} must be an HTTPS URL without credentials, query, or fragment")
    return value.rstrip("/")


def load_manifest(filename, expected_sha, allow_dirty=False):
    filename = Path(filename)
    require(not filename.is_symlink(), "Manifest must not be a symlink")
    require(filename.stat().st_size <= 2_000_000, "Manifest is too large")
    data = json.loads(filename.read_text())
    require(data.get("schemaVersion") == 1, "Unsupported manifest version")
    require(re.fullmatch(r"[a-f0-9]{40}", data.get("headSha", "")), "Invalid head SHA")
    require(data["headSha"] == expected_sha, "Evidence does not match the expected PR head SHA")
    require(allow_dirty or data.get("worktreeDirty") is False, "Record committed, clean source before publishing")
    require(re.fullmatch(r"run-[a-z0-9-]{1,100}", data.get("runId", "")), "Invalid run identifier")
    require(data.get("status") in {"passed", "failed"}, "Invalid run status")
    tests = data.get("tests")
    require(isinstance(tests, list) and 0 < len(tests) <= 200, "Evidence must contain test results")
    files = {}
    for test in tests:
        require(isinstance(test.get("title"), str) and len(test["title"]) <= 2000, "Invalid test title")
        require(test.get("status") in {"passed", "failed", "timedOut", "skipped", "interrupted"}, "Invalid test status")
        for asset in test.get("assets", []):
            relative = asset.get("file", "")
            require(re.fullmatch(r"assets/[a-f0-9]{16}-\d+-\d+\.(webm|mp4|png)", relative), "Invalid media path")
            target = filename.parent / relative
            require(not any(p.is_symlink() for p in [target, target.parent, filename.parent]), "Media paths must not contain symlinks")
            require(target.resolve().is_relative_to(filename.parent.resolve()), "Media escaped the run directory")
            content_type = TYPES[PurePosixPath(relative).suffix]
            require(asset.get("contentType") == content_type, "Media type mismatch")
            require(target.stat().st_size <= 100_000_000, "Media exceeds the 100 MB limit")
            content = target.read_bytes()
            require(len(content) == asset.get("size") and hashlib.sha256(content).hexdigest() == asset.get("sha256"), "Media checksum mismatch")
            signature_ok = (content.startswith(b"\x89PNG\r\n\x1a\n") if content_type == "image/png"
                            else content.startswith(b"\x1aE\xdf\xa3") if content_type == "video/webm"
                            else content[4:8] == b"ftyp")
            require(signature_ok, "Media signature mismatch")
            files[relative] = (content, content_type)
    require(0 < len(files) <= 400, "No publishable media, or too many files")
    if data["status"] == "passed":
        require(len(tests) == data.get("expectedTests") and data.get("runnerErrors") == 0
                and all(t["status"] == "passed" and t.get("retry") == 0
                        and any(a.get("contentType", "").startswith("video/") for a in t.get("assets", [])) for t in tests),
                "A passing report requires every scenario to pass with a recording and no retries")
    return data, files


def signed_request(url, content, content_type, access_key, secret_key, region, session_token=None, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    parsed = urllib.parse.urlsplit(url)
    payload_hash = hashlib.sha256(content).hexdigest()
    headers = {"host": parsed.netloc, "content-type": content_type,
               "x-amz-content-sha256": payload_hash, "x-amz-date": timestamp}
    if session_token:
        headers["x-amz-security-token"] = session_token
    names = ";".join(sorted(headers))
    canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in sorted(headers))
    canonical_request = "\n".join(["PUT", parsed.path or "/", "", canonical_headers, names, payload_hash])
    scope = f"{date}/{region}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", timestamp, scope, hashlib.sha256(canonical_request.encode()).hexdigest()])
    key = ("AWS4" + secret_key).encode()
    for item in [date, region, "s3", "aws4_request"]:
        key = hmac.new(key, item.encode(), hashlib.sha256).digest()
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={names}, Signature={signature}"
    return urllib.request.Request(url, data=content, method="PUT", headers=headers)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, _request, _fp, _code, _msg, _headers, _url):
        raise EvidenceError("Storage redirect refused; configure the exact bucket endpoint")


def upload(request):
    # Inherited HTTPS_PROXY and system CA trust remain in use.
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            require(200 <= response.status < 300, "Storage did not accept the upload")
    except urllib.error.HTTPError as error:
        raise EvidenceError(f"Storage upload failed (HTTP {error.code}); check endpoint, policy, and credentials") from None
    except urllib.error.URLError:
        raise EvidenceError("Storage connection failed; check proxy, CA trust, and destination policy") from None


def verify_media_url(url, content_type):
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            require(200 <= response.status < 300 and response.headers.get_content_type() == content_type,
                    "Published media URL is unavailable or has an unexpected content type")
    except urllib.error.HTTPError as error:
        raise EvidenceError(f"Published media URL is not readable (HTTP {error.code}); check bucket delivery settings") from None
    except urllib.error.URLError:
        raise EvidenceError("Published media URL could not be reached; check delivery URL and destination policy") from None


def markdown(data, urls, published):
    def clean(text):
        return re.sub(r"[\r\n|<>`\\\[\]]", " ", text)[:500]
    lines = [MARKER, "## ブラウザ検証の証跡", "",
             f"結果: **{data['status']}** / 検証したhead: `{data['headSha']}`",
             "合成データを使ったWebブラウザ検証です。", "",
             "| 操作シナリオ | 結果 | 動画・画面 |", "| --- | --- | --- |"]
    for test in data["tests"]:
        links = [f"[{'動画' if a['contentType'].startswith('video/') else '画面'}]({urls[a['file']]})" for a in test.get("assets", [])]
        lines.append(f"| {clean(test['title'])} | {test['status']} | {' · '.join(links)} |")
    if not published:
        lines += ["", "**dry-run: ストレージ保存・PR掲載は未実行です。**"]
    return "\n".join(lines) + "\n"


def gh_json(arguments):
    result = subprocess.run(["gh", "api", *arguments], capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, "GitHub API operation failed; check authentication, access, and network policy")
    return json.loads(result.stdout)


def post_comment(repo, pr_number, expected_sha, body):
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo), "Invalid repository")
    pr = gh_json([f"repos/{repo}/pulls/{pr_number}"])
    require(pr.get("state") == "open" and pr["head"]["sha"] == expected_sha, "PR is closed or its head changed; rerun evidence")
    require(pr["head"]["repo"]["full_name"].lower() == repo.lower(), "Publishing is limited to same-repository PRs")
    pages = gh_json(["--paginate", "--slurp", f"repos/{repo}/issues/{pr_number}/comments?per_page=100"])
    comments = [comment for page in pages for comment in page]
    actor = "github-actions[bot]" if os.environ.get("GITHUB_ACTIONS") == "true" else gh_json(["user"])["login"]
    existing = [comment for comment in comments if comment.get("user", {}).get("login") == actor and comment.get("body", "").startswith(MARKER)]
    endpoint = f"repos/{repo}/issues/comments/{existing[-1]['id']}" if existing else f"repos/{repo}/issues/{pr_number}/comments"
    method = "PATCH" if existing else "POST"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as payload:
        json.dump({"body": body}, payload)
        payload.flush()
        written = gh_json(["--method", method, endpoint, "--input", payload.name])
    readback = gh_json([f"repos/{repo}/issues/comments/{written['id']}"])
    require(readback.get("body") == body, "PR comment readback did not match")
    return readback["html_url"]


def publish(manifest_path, expected_sha, apply=False, repo=None, pr_number=None, comment=False):
    data, files = load_manifest(manifest_path, expected_sha, allow_dirty=not apply)
    endpoint = https_url(os.environ.get("EVIDENCE_S3_ENDPOINT", ""), "EVIDENCE_S3_ENDPOINT")
    public_base = https_url(os.environ.get("EVIDENCE_PUBLIC_BASE_URL", ""), "EVIDENCE_PUBLIC_BASE_URL")
    bucket = os.environ.get("EVIDENCE_S3_BUCKET", "")
    require(re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket), "Set a valid EVIDENCE_S3_BUCKET")
    prefix = os.environ.get("EVIDENCE_KEY_PREFIX") or "browser-evidence"
    require(re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", prefix), "Invalid EVIDENCE_KEY_PREFIX")
    prefix = f"{prefix}/{data['headSha']}/{data['runId']}"
    urls = {relative: f"{public_base}/{urllib.parse.quote(prefix + '/' + relative, safe='/')}" for relative in files}
    if apply:
        access_key = os.environ.get("EVIDENCE_S3_ACCESS_KEY_ID", "")
        secret_key = os.environ.get("EVIDENCE_S3_SECRET_ACCESS_KEY", "")
        require(access_key and secret_key, "Set storage credentials in the environment's Secret store")
        region = os.environ.get("EVIDENCE_S3_REGION") or "auto"
        require(re.fullmatch(r"[a-z0-9-]+", region), "Invalid storage region")
        if comment:
            require(repo and pr_number, "PR comment requires --repo and --pr")
            require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) and pr_number > 0, "Invalid repository or PR number")
            pr = gh_json([f"repos/{repo}/pulls/{pr_number}"])
            require(pr.get("state") == "open" and pr["head"]["sha"] == expected_sha
                    and pr["head"]["repo"]["full_name"].lower() == repo.lower(), "PR head or repository does not match")
        for relative, (content, content_type) in files.items():
            key = urllib.parse.quote(prefix + "/" + relative, safe="/")
            request = signed_request(f"{endpoint}/{bucket}/{key}", content, content_type, access_key, secret_key, region,
                                     os.environ.get("EVIDENCE_S3_SESSION_TOKEN"))
            upload(request)
        for relative, (_, content_type) in files.items():
            verify_media_url(urls[relative], content_type)
    body = markdown(data, urls, apply)
    directory = Path(manifest_path).parent
    report = directory / "pr-body.md"
    report.write_text(body)
    receipt = {"mode": "published" if apply else "dry-run", "headSha": data["headSha"], "status": data["status"], "urls": urls}
    if comment and apply:
        receipt["commentUrl"] = post_comment(repo, pr_number, expected_sha, body)
    (directory / "publish.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return {"mode": receipt["mode"], "mediaCount": len(files), "report": str(report), "commentUrl": receipt.get("commentUrl")}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", required=True)
    cli.add_argument("--expected-sha", required=True)
    mode = cli.add_mutually_exclusive_group()
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    cli.add_argument("--comment", action="store_true")
    cli.add_argument("--repo")
    cli.add_argument("--pr", type=int)
    args = cli.parse_args()
    try:
        result = publish(args.manifest, args.expected_sha, args.publish, args.repo, args.pr, args.comment)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Never print request headers, credentials, or an arbitrary remote response.
        message = str(error) if isinstance(error, EvidenceError) else "Invalid evidence input or local tool failure"
        print(f"ERROR: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
