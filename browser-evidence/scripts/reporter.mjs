import { copyFile, mkdir, readFile, realpath, writeFile } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";

const types = new Map([
  ["video/webm", ".webm"], ["video/mp4", ".mp4"], ["image/png", ".png"],
]);
const escape = (value) => String(value).replace(/[\r\n]/gu, " ").replace(/[|<>`\\]/gu, " ").slice(0, 500);

export default class EvidenceReporter {
  constructor() {
    this.directory = process.env.BROWSER_EVIDENCE_OUTPUT_DIR;
    this.tests = [];
    this.errors = [];
  }

  onBegin(_config, suite) {
    if (!this.directory) throw new Error("Use browser-evidence/scripts/run.mjs to create an evidence run.");
    this.total = suite.allTests().length;
    this.startedAt = new Date().toISOString();
  }

  onError() {
    // Error details remain in Playwright's local output, outside published media.
    this.errors.push("runner-error");
  }

  onTestEnd(test, result) {
    this.tests.push({
      title: test.titlePath().filter(Boolean).join(" / "),
      status: result.status,
      durationMs: result.duration,
      retry: result.retry,
      assets: [],
      id: test.id,
      attachments: result.attachments,
    });
  }

  async collectAssets(test) {
    const id = createHash("sha256").update(test.id).digest("hex").slice(0, 16);
    const assets = [];
    const rawRoot = await realpath(path.join(this.directory, "raw"));
    await mkdir(path.join(this.directory, "assets"), { recursive: true });
    for (const [index, attachment] of test.attachments.entries()) {
      const extension = types.get(attachment.contentType);
      if (!extension || !attachment.path) continue;
      const source = await realpath(attachment.path);
      const relative = path.relative(rawRoot, source);
      if (relative.startsWith("..") || path.isAbsolute(relative)) throw new Error("Evidence attachment is outside the test output.");
      const file = `assets/${id}-${test.retry}-${index}${extension}`;
      await copyFile(source, path.join(this.directory, file));
      const bytes = await readFile(path.join(this.directory, file));
      assets.push({ file, contentType: attachment.contentType, size: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex") });
    }
    return assets;
  }

  async onEnd(result) {
    if (!this.directory) return;
    for (const test of this.tests) {
      if (test.attachments.some((attachment) => types.has(attachment.contentType) && attachment.path)) {
        test.assets = await this.collectAssets(test);
      }
      delete test.id;
      delete test.attachments;
    }
    const complete = this.tests.length === this.total && this.total > 0;
    const passed = result.status === "passed" && complete && this.errors.length === 0 && this.tests.every((test) => test.status === "passed" && test.assets.some((asset) => asset.contentType.startsWith("video/")));
    const manifest = {
      schemaVersion: 1,
      runId: process.env.BROWSER_EVIDENCE_RUN_ID,
      headSha: process.env.BROWSER_EVIDENCE_HEAD_SHA,
      worktreeDirty: process.env.BROWSER_EVIDENCE_DIRTY !== "false",
      startedAt: this.startedAt,
      finishedAt: new Date().toISOString(),
      status: passed ? "passed" : "failed",
      expectedTests: this.total,
      runnerErrors: this.errors.length,
      tests: this.tests,
    };
    await mkdir(this.directory, { recursive: true });
    await writeFile(path.join(this.directory, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
    const lines = [
      "# Browser evidence", "",
      `Result: **${manifest.status}**`,
      `Head: \`${manifest.headSha}\``,
      `Uncommitted changes: ${manifest.worktreeDirty}`, "",
      "| Scenario | Result | Evidence |", "| --- | --- | --- |",
      ...this.tests.map((test) => `| ${escape(test.title)} | ${test.status} | ${test.assets.map((asset) => `[${asset.contentType.startsWith("video/") ? "video" : "screen"}](${asset.file})`).join(" · ")} |`),
      "", "Local evidence only. Storage upload and PR comment have not been performed.", "",
    ];
    await writeFile(path.join(this.directory, "summary.md"), lines.join("\n"));
    if (!passed && result.status === "passed") return { status: "failed" };
  }
}
