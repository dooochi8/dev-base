import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import test from "node:test";

const script = fileURLToPath(new URL("../scripts/stage.mjs", import.meta.url));

test("CI staging copies only the selected media and manifest into a visible upload directory", async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), "browser-evidence-stage-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const run = path.join(root, ".artifacts/browser-evidence/run-test");
  await mkdir(path.join(run, "assets"), { recursive: true });
  await mkdir(path.join(run, "raw"));
  const file = "assets/1234567890abcdef-0-0.webm";
  await writeFile(path.join(run, file), "video");
  await writeFile(path.join(run, "raw/trace.zip"), "private details");
  await writeFile(path.join(root, ".artifacts/browser-evidence/latest.json"), JSON.stringify({ directory: run }));
  await writeFile(path.join(run, "manifest.json"), JSON.stringify({ status: "passed", tests: [{ assets: [{ file }] }] }));
  const result = spawnSync(process.execPath, [script], { cwd: root, encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  const upload = path.join(root, "tmp/browser-evidence-upload");
  assert.deepEqual((await readdir(upload)).sort(), ["assets", "manifest.json"]);
  assert.equal(await readFile(path.join(upload, file), "utf8"), "video");
  await writeFile(path.join(run, "manifest.json"), JSON.stringify({ tests: [{ assets: [{ file: "../private.png" }] }] }));
  assert.notEqual(spawnSync(process.execPath, [script], { cwd: root }).status, 0);
});
