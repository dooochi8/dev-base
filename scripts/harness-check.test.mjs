import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { globToRegExp, run } from "./harness-check.mjs";

const config = {
  include: ["src/**/*.ts"],
  exclude: ["**/*.test.ts"],
  rules: [
    { id: "raw-timer", pattern: "\\bsetTimeout\\s*\\(", allow: ["src/platform/**"], message: "use the scheduler" },
    { id: "domain-react", pattern: "from \"react\"", include: ["src/domain/**"], message: "keep React out of the domain" },
  ],
};

function project(files) {
  const root = mkdtempSync(path.join(tmpdir(), "harness-"));
  writeFileSync(path.join(root, "harness.config.json"), JSON.stringify(config));
  for (const [file, content] of Object.entries(files)) {
    mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
    writeFileSync(path.join(root, file), content);
  }
  return root;
}

function check(root, ...flags) {
  const output = [];
  const code = run(["--root", root, ...flags], (line) => output.push(line));
  return { code, output: output.join("\n") };
}

function baselineOf(root) {
  return JSON.parse(readFileSync(path.join(root, "harness-baseline.json"), "utf8"));
}

test("globToRegExp matches nested and single segments", () => {
  assert.ok(globToRegExp("src/**/*.ts").test("src/a.ts"));
  assert.ok(globToRegExp("src/**/*.ts").test("src/a/b/c.ts"));
  assert.ok(!globToRegExp("src/*.ts").test("src/a/b.ts"));
  assert.ok(globToRegExp("apps/*/src/**").test("apps/demo/src/x/y.tsx"));
});

test("passes when nothing matches", () => {
  assert.equal(check(project({ "src/a.ts": "export const a = 1;\n" })).code, 0);
});

test("fails on a new occurrence with the rule message and location", () => {
  const { code, output } = check(project({ "src/a.ts": "const x = 1;\nsetTimeout(run, 0);\n" }));
  assert.equal(code, 1);
  assert.match(output, /\[raw-timer\] src\/a\.ts/);
  assert.match(output, /src\/a\.ts:2/);
  assert.match(output, /use the scheduler/);
});

test("allow, exclude and per-rule include are respected", () => {
  const root = project({
    "src/platform/scheduler.ts": "setTimeout(run, 0);\n",
    "src/a.test.ts": "setTimeout(run, 0);\n",
    "src/ui/view.ts": "import { useState } from \"react\";\n",
    "lib/other.ts": "setTimeout(run, 0);\n",
  });
  assert.equal(check(root).code, 0);
  const domain = project({ "src/domain/log.ts": "import { useState } from \"react\";\n" });
  assert.match(check(domain).output, /domain-react/);
});

test("init records existing debt, then only increases fail", () => {
  const root = project({ "src/a.ts": "setTimeout(a, 0);\n" });
  assert.equal(check(root, "--init").code, 0);
  assert.deepEqual(baselineOf(root), { "raw-timer": { "src/a.ts": 1 } });
  assert.equal(check(root).code, 0);
  writeFileSync(path.join(root, "src/a.ts"), "setTimeout(a, 0);\nsetTimeout(b, 0);\n");
  assert.equal(check(root).code, 1);
  writeFileSync(path.join(root, "src/b.ts"), "setTimeout(c, 0);\n");
  writeFileSync(path.join(root, "src/a.ts"), "setTimeout(a, 0);\n");
  assert.match(check(root).output, /src\/b\.ts: 1 found, 0 allowed/);
});

test("init refuses to overwrite an existing baseline", () => {
  const root = project({ "src/a.ts": "setTimeout(a, 0);\n" });
  check(root, "--init");
  assert.equal(check(root, "--init").code, 1);
});

test("a fixed occurrence fails until pruned, and prune never grows the baseline", () => {
  const root = project({ "src/a.ts": "setTimeout(a, 0);\nsetTimeout(b, 0);\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "setTimeout(a, 0);\n");
  const stale = check(root);
  assert.equal(stale.code, 1);
  assert.match(stale.output, /--prune/);
  writeFileSync(path.join(root, "src/new.ts"), "setTimeout(n, 0);\n");
  assert.equal(check(root, "--prune").code, 0);
  assert.deepEqual(baselineOf(root), { "raw-timer": { "src/a.ts": 1 } });
  assert.equal(check(root).code, 1);
});

test("unknown arguments are rejected", () => {
  assert.throws(() => run(["--root", project({}), "--force"], () => {}), /Unknown argument/);
});
