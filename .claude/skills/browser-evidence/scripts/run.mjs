import { spawn, execFileSync } from "node:child_process";
import { mkdir, readFile, symlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { randomUUID } from "node:crypto";

const root = process.cwd();
const require = createRequire(path.join(root, "package.json"));
const cli = require.resolve("@playwright/test/cli");
const git = (...args) => execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
const headSha = git("rev-parse", "HEAD");
const dirty = git("status", "--porcelain").length > 0;
const runId = `run-${new Date().toISOString().replace(/[^0-9]/gu, "")}-${randomUUID().slice(0, 8)}`;
const output = path.join(root, ".artifacts", "browser-evidence", runId);
await mkdir(output, { recursive: true });
const browserEnvironment = {};
if (process.env.BROWSER_EVIDENCE_SYSTEM_FFMPEG) {
  // Use an explicitly selected, installed ffmpeg without downloading browser tools.
  const ffmpeg = path.resolve(process.env.BROWSER_EVIDENCE_SYSTEM_FFMPEG);
  const playwrightRequire = createRequire(createRequire(cli).resolve("playwright/package.json"));
  const registry = JSON.parse(await readFile(path.join(path.dirname(playwrightRequire.resolve("playwright-core/package.json")), "browsers.json"), "utf8"));
  const revision = registry.browsers.find((browser) => browser.name === "ffmpeg").revision;
  const cache = path.join(output, "browser-tools");
  const directory = path.join(cache, `ffmpeg-${revision}`);
  await mkdir(directory, { recursive: true });
  const name = process.platform === "darwin" ? "ffmpeg-mac" : process.platform === "win32" ? "ffmpeg-win64.exe" : "ffmpeg-linux";
  await symlink(ffmpeg, path.join(directory, name));
  browserEnvironment.PLAYWRIGHT_BROWSERS_PATH = cache;
}
const args = process.argv.slice(2).filter((arg, index) => !(index === 0 && arg === "--"));
const child = spawn(process.execPath, [cli, "test", "--config", "playwright.evidence.config.mjs", ...args], {
  cwd: root,
  stdio: "inherit",
  detached: process.platform !== "win32",
  env: {
    ...process.env,
    ...browserEnvironment,
    BROWSER_EVIDENCE_OUTPUT_DIR: output,
    BROWSER_EVIDENCE_RUN_ID: runId,
    BROWSER_EVIDENCE_HEAD_SHA: headSha,
    BROWSER_EVIDENCE_DIRTY: String(dirty),
  },
});
let killTimer;
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    const stop = (value) => {
      try {
        if (process.platform === "win32") child.kill(value);
        else process.kill(-child.pid, value);
      } catch { /* The process group may already have exited. */ }
    };
    stop(signal);
    killTimer ??= setTimeout(() => stop("SIGKILL"), 5000).unref();
  });
}
const exitCode = await new Promise((resolve, reject) => {
  child.once("error", reject);
  child.once("exit", (code) => resolve(code ?? 1));
});
clearTimeout(killTimer);
await writeFile(path.join(root, ".artifacts", "browser-evidence", "latest.json"), JSON.stringify({ runId, directory: output }, null, 2) + "\n");
console.log(`Browser evidence: ${output}`);
try {
  const manifest = JSON.parse(await readFile(path.join(output, "manifest.json"), "utf8"));
  process.exitCode = exitCode || (manifest.status === "passed" ? 0 : 1);
} catch {
  console.error("Evidence manifest was not generated; this run is not verified.");
  process.exitCode = exitCode || 1;
}
