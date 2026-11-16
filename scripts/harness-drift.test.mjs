import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { digest, inspectCopy, run } from "./harness-drift.mjs";

const canonicalSource = readFileSync(new URL("./harness-check.mjs", import.meta.url), "utf8");
const goodRule = {
  id: "raw-timer",
  pattern: "\\bsetTimeout\\s*\\(",
  message: "use the scheduler",
  examples: { bad: ["setTimeout(run, 0);"], good: ["clearTimeout(handle);"] },
};

function repository({ checker = canonicalSource, rules = [goodRule] } = {}) {
  const root = mkdtempSync(path.join(tmpdir(), "harness-drift-"));
  mkdirSync(path.join(root, "scripts"));
  if (checker !== null) writeFileSync(path.join(root, "scripts/harness-check.mjs"), checker);
  if (rules !== null) writeFileSync(path.join(root, "harness.config.json"), JSON.stringify({ include: ["src/**"], rules }));
  return root;
}

function check(...roots) {
  const lines = [];
  const code = run(roots, { log: (line) => lines.push(line), canonicalSource });
  return { code, output: lines.join("\n") };
}

test("正本と同じコピーで、全ルールが self-test を通れば成功する", () => {
  const { code, output } = check(repository());
  assert.equal(code, 0, output);
  assert.match(output, new RegExp(`正本（${digest(canonicalSource)}）と同じ`, "u"));
});

test("古いコピーは、両方のハッシュを示して失敗する", () => {
  const old = `${canonicalSource}\n`;
  const { code, output } = check(repository({ checker: old }));
  assert.equal(code, 1);
  assert.match(output, new RegExp(`正本と違う（${digest(old)}、正本は ${digest(canonicalSource)}）`, "u"));
});

test("examples のないルールや、悪例を捕まえないルールは self-test で失敗する", () => {
  const { examples, ...withoutExamples } = goodRule;
  assert.ok(examples.bad.length > 0);
  const result = inspectCopy({ name: "x", checkerSource: canonicalSource, config: { rules: [withoutExamples] }, canonicalSource });
  assert.match(result.problems.join("\n"), /self-test: \[raw-timer\] needs examples/u);
  const missing = inspectCopy({ name: "x", checkerSource: canonicalSource, config: { rules: [{ ...goodRule, pattern: "never-matches" }] }, canonicalSource });
  assert.match(missing.problems.join("\n"), /misses bad example/u);
});

test("ファイルがなければ、それを指摘して失敗する。複数のリポジトリは全部見る", () => {
  const { code, output } = check(repository(), repository({ checker: null, rules: null }));
  assert.equal(code, 1);
  assert.match(output, /scripts\/harness-check\.mjs がない/u);
  assert.match(output, /harness\.config\.json がない/u);
  assert.match(output, /1件のリポジトリがずれている/u);
});

test("引数がなければ使い方を出して 2 を返す", () => {
  assert.equal(run([], { log: () => {}, canonicalSource }), 2);
});

test("壊れた設定 JSON はそのリポジトリの問題として示し、残りのリポジトリも照合する", () => {
  const broken = repository();
  writeFileSync(path.join(broken, "harness.config.json"), "{ not json");
  const { code, output } = check(broken, repository());
  assert.equal(code, 1);
  assert.match(output, /harness\.config\.json を JSON として読めない/u);
  assert.match(output, /✔ harness-drift-/u);
  assert.match(output, /1件のリポジトリがずれている/u);
});
