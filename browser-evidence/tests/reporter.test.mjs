import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import Reporter from "../scripts/reporter.mjs";

async function fixture(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), "browser-evidence-test-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const previous = { ...process.env };
  Object.assign(process.env, { BROWSER_EVIDENCE_OUTPUT_DIR: directory, BROWSER_EVIDENCE_RUN_ID: "run-test", BROWSER_EVIDENCE_HEAD_SHA: "a".repeat(40), BROWSER_EVIDENCE_DIRTY: "false" });
  t.after(() => { process.env = previous; });
  await mkdir(path.join(directory, "raw"));
  const media = path.join(directory, "raw/video.webm");
  await writeFile(media, Buffer.from([0x1a, 0x45, 0xdf, 0xa3]));
  const reporter = new Reporter();
  reporter.onBegin({}, { allTests: () => [{}] });
  return { directory, media, reporter };
}

test("success requires a finished scenario and a copied recording; raw details are excluded", async (t) => {
  const { directory, media, reporter } = await fixture(t);
  reporter.onTestEnd({ id: "scenario", titlePath: () => ["registration"] }, {
    status: "passed", duration: 100, retry: 0,
    attachments: [{ path: media, contentType: "video/webm" }, { body: Buffer.from("private response"), contentType: "application/json" }],
  });
  await reporter.onEnd({ status: "passed" });
  const manifest = JSON.parse(await readFile(path.join(directory, "manifest.json"), "utf8"));
  assert.equal(manifest.status, "passed");
  assert.equal(manifest.tests[0].assets.length, 1);
  assert.equal(manifest.tests[0].assets[0].size, 4);
  assert.equal("attachments" in manifest.tests[0], false);
  assert.equal((await readFile(path.join(directory, manifest.tests[0].assets[0].file))).length, 4);
});

test("no recording, skipped tests, runner errors, and empty runs fail the evidence gate", async (t) => {
  for (const kind of ["no-video", "skipped", "runner-error", "empty"]) {
    await t.test(kind, async (t) => {
      const { directory, media, reporter } = await fixture(t);
      if (kind !== "empty") reporter.onTestEnd({ id: kind, titlePath: () => [kind] }, {
        status: kind === "skipped" ? "skipped" : "passed", duration: 1, retry: 0,
        attachments: kind === "no-video" ? [] : [{ path: media, contentType: "video/webm" }],
      });
      if (kind === "runner-error") reporter.onError(new Error("private error"));
      assert.deepEqual(await reporter.onEnd({ status: "passed" }), { status: "failed" });
      const manifest = JSON.parse(await readFile(path.join(directory, "manifest.json"), "utf8"));
      assert.equal(manifest.status, "failed");
    });
  }
});
