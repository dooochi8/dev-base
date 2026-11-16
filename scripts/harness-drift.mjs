#!/usr/bin/env node
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { selfTest } from "./harness-check.mjs";

const canonicalPath = fileURLToPath(new URL("./harness-check.mjs", import.meta.url));

export function digest(source) {
  return createHash("sha256").update(source).digest("hex").slice(0, 12);
}

export function inspectCopy({ name, checkerSource, config, canonicalSource }) {
  const problems = [];
  if (checkerSource === null) problems.push("scripts/harness-check.mjs がない");
  else if (checkerSource !== canonicalSource) problems.push(`scripts/harness-check.mjs が正本と違う（${digest(checkerSource)}、正本は ${digest(canonicalSource)}）`);
  if (config === null) problems.push("harness.config.json がない");
  else for (const failure of selfTest(config)) problems.push(`self-test: ${failure}`);
  return { name, problems };
}

function readIfExists(file) {
  return existsSync(file) ? readFileSync(file, "utf8") : null;
}

export function run(argv, { log = console.log, canonicalSource = readFileSync(canonicalPath, "utf8") } = {}) {
  if (argv.length === 0) {
    log("使い方: node scripts/harness-drift.mjs <複製先リポジトリのパス>...");
    return 2;
  }
  let drifted = 0;
  for (const repository of argv) {
    const configSource = readIfExists(path.join(repository, "harness.config.json"));
    const result = inspectCopy({
      name: path.basename(path.resolve(repository)),
      checkerSource: readIfExists(path.join(repository, "scripts/harness-check.mjs")),
      config: configSource === null ? null : JSON.parse(configSource),
      canonicalSource,
    });
    if (result.problems.length === 0) {
      log(`✔ ${result.name}: 正本（${digest(canonicalSource)}）と同じで、全ルールが self-test を通る`);
      continue;
    }
    drifted += 1;
    log(`✖ ${result.name}`);
    for (const problem of result.problems) log(`    ${problem}`);
  }
  if (drifted > 0) {
    log(`\n${drifted}件のリポジトリがずれている。scripts/harness-check.mjs を正本からそのまま写し、各ルールに examples（bad と good）を書く。`);
    return 1;
  }
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = run(process.argv.slice(2));
}
