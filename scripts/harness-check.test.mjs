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
  assert.deepEqual(baselineOf(root), { adopted: ["domain-react", "raw-timer"], "raw-timer": { "src/a.ts": 1 } });
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
  assert.deepEqual(baselineOf(root), { adopted: ["domain-react", "raw-timer"], "raw-timer": { "src/a.ts": 1 } });
  assert.equal(check(root).code, 1);
});

test("unknown arguments are rejected", () => {
  assert.throws(() => run(["--root", project({}), "--force"], () => {}), /Unknown argument/);
});

test("adopt records debt for a newly added rule exactly once", () => {
  const root = project({ "src/a.ts": "setTimeout(a, 0);\n" });
  writeFileSync(path.join(root, "harness-baseline.json"), JSON.stringify({ adopted: ["domain-react"] }));
  assert.equal(check(root).code, 1);
  assert.equal(check(root, "--adopt", "raw-timer").code, 0);
  assert.deepEqual(baselineOf(root), { adopted: ["domain-react", "raw-timer"], "raw-timer": { "src/a.ts": 1 } });
  assert.equal(check(root).code, 0);
  assert.equal(check(root, "--adopt", "raw-timer").code, 1);
  assert.equal(check(root, "--adopt", "domain-react").code, 1);
  assert.equal(check(root, "--adopt", "missing-rule").code, 1);
});

test("prune keeps the adopted list", () => {
  const root = project({ "src/a.ts": "setTimeout(a, 0);\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "export {};\n");
  check(root, "--prune");
  assert.deepEqual(baselineOf(root), { adopted: ["domain-react", "raw-timer"] });
  assert.equal(check(root).code, 0);
});

test("counts every occurrence on the same line", () => {
  const root = project({ "src/a.ts": "setTimeout(a, 0);\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "setTimeout(a, 0); setTimeout(b, 0);\n");
  const { code, output } = check(root);
  assert.equal(code, 1);
  assert.match(output, /src\/a\.ts: 2 found, 1 allowed/);
});

test("the template rules catch any in every type position and inline block comments", () => {
  const template = JSON.parse(readFileSync(new URL("../templates/harness/harness.config.json", import.meta.url), "utf8"));
  const pattern = (id) => new RegExp(template.rules.find((rule) => rule.id === id).pattern);
  const anyRule = pattern("explicit-any");
  for (const line of ["let a: any;", "x as any", "type X = any;", "Record<string, any>", "string | any", "Array<any>", "any[]", "f(a, any)"]) {
    assert.ok(anyRule.test(line), line);
  }
  for (const line of ["const anyValue = 1;", "if (items.some(Boolean)) {}", "const many = 2;", "const message = \"pick any\";"]) {
    assert.ok(!anyRule.test(line), line);
  }
  const commentRule = pattern("code-comment");
  for (const line of ["// note", "/* note */", " * note", "run(); // note", "const x = /* note */ 1;", "foo(/* note */ value);"]) {
    assert.ok(commentRule.test(line), line);
  }
  for (const line of ["const url = \"https://example.com\";", "const glob = \"src/**/*.ts\";", "/// <reference types=\"vite/client\" />", "const total = a * b;"]) {
    assert.ok(!commentRule.test(line), line);
  }
});

function selfTest(rules) {
  const root = mkdtempSync(path.join(tmpdir(), "harness-self-"));
  writeFileSync(path.join(root, "harness.config.json"), JSON.stringify({ include: ["src/**"], rules }));
  return check(root, "--self-test");
}

const timerRule = {
  id: "raw-timer",
  pattern: "\\bsetTimeout\\s*\\(",
  message: "use the scheduler",
  examples: { bad: ["setTimeout(run, 0);"], good: ["clearTimeout(handle);", "scheduler.after(delay, run);"] },
};

test("self-test passes when every rule catches its bad examples and spares its good ones", () => {
  const { code, output } = selfTest([timerRule]);
  assert.equal(code, 0, output);
  assert.match(output, /1 rules/);
});

test("self-test fails on a bad example the pattern misses", () => {
  const rule = { ...timerRule, examples: { ...timerRule.examples, bad: ["setTimeout(run, 0);", "setInterval(run, 10);"] } };
  const { code, output } = selfTest([rule]);
  assert.equal(code, 1);
  assert.match(output, /\[raw-timer\] misses bad example: setInterval\(run, 10\);/);
});

test("self-test fails on a good example the pattern flags", () => {
  const rule = { ...timerRule, pattern: "Timeout\\s*\\(" };
  const { code, output } = selfTest([rule]);
  assert.equal(code, 1);
  assert.match(output, /\[raw-timer\] flags good example: clearTimeout\(handle\);/);
});

test("self-test requires both bad and good examples", () => {
  for (const examples of [undefined, { bad: ["setTimeout(run, 0);"] }, { bad: [], good: ["run();"] }]) {
    const { code, output } = selfTest([{ ...timerRule, examples }]);
    assert.equal(code, 1);
    assert.match(output, /\[raw-timer\] needs examples\.bad and examples\.good/);
  }
});

test("self-test does not read the baseline or scan files", () => {
  const root = project({ "src/a.ts": "setTimeout(a, 0);\n" });
  writeFileSync(path.join(root, "harness.config.json"), JSON.stringify({ ...config, rules: [timerRule] }));
  assert.equal(check(root, "--self-test").code, 0);
});

test("the shipped template rules pass their own self-test", () => {
  const template = path.join(import.meta.dirname, "..", "templates", "harness", "harness.config.json");
  const output = [];
  const code = run(["--config", template, "--self-test"], (line) => output.push(line));
  assert.equal(code, 0, output.join("\n"));
});

test("self-test matches lines the same way as the scan, even with a g flag", () => {
  const rule = { ...timerRule, flags: "g", examples: { bad: ["setTimeout(a, 0);", "setTimeout(b, 0);"], good: ["run();"] } };
  assert.equal(selfTest([rule]).code, 0);
});
