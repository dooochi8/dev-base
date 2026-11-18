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

const commentRule = { id: "code-comment", pattern: "//", baseline: "text", message: "move the comment into a name, type or test" };

function textProject(files, rules = [commentRule]) {
  const root = mkdtempSync(path.join(tmpdir(), "harness-text-"));
  writeFileSync(path.join(root, "harness.config.json"), JSON.stringify({ include: ["src/**/*.ts"], rules }));
  for (const [file, content] of Object.entries(files)) {
    mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
    writeFileSync(path.join(root, file), content);
  }
  return root;
}

test("a text-baseline rule records each finding's text, not only the count", () => {
  const root = textProject({ "src/a.ts": "run(); // keep the lease\n// keep the lease\n// retry is safe\n" });
  assert.equal(check(root, "--init").code, 0);
  assert.deepEqual(baselineOf(root)["code-comment"], { "src/a.ts": { "// keep the lease": 2, "// retry is safe": 1 } });
  assert.equal(check(root).code, 0);
});

test("rewriting a kept comment fails even when the count stays the same", () => {
  const root = textProject({ "src/a.ts": "// retry is safe\nrun();\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "// retry is always safe\nrun();\n");
  const { code, output } = check(root);
  assert.equal(code, 1);
  assert.match(output, /\[code-comment\] src\/a\.ts: 1 new or rewritten/);
  assert.match(output, /src\/a\.ts:1  \/\/ retry is always safe/);
  assert.match(output, /▲ \[code-comment\] src\/a\.ts: 1 recorded text no longer found/);
});

test("moving a kept comment to another line still passes", () => {
  const root = textProject({ "src/a.ts": "// retry is safe\nrun();\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "import { run } from \"./run\";\n\nrun();\n// retry is safe\n");
  assert.equal(check(root).code, 0);
});

test("the same text may appear only as many times as recorded", () => {
  const root = textProject({ "src/a.ts": "// same\n// same\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "// same\n// same\n// same\n");
  assert.match(check(root).output, /1 new or rewritten/);
});

test("removing a kept comment must be pruned per text, and prune never re-allows a new text", () => {
  const root = textProject({ "src/a.ts": "// one\n// two\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "// one\n");
  const stale = check(root);
  assert.equal(stale.code, 1);
  assert.match(stale.output, /--prune/);
  writeFileSync(path.join(root, "src/a.ts"), "// one\n// three\n");
  check(root, "--prune");
  assert.deepEqual(baselineOf(root)["code-comment"], { "src/a.ts": { "// one": 1 } });
  assert.match(check(root).output, /1 new or rewritten/);
});

test("migrate-text turns a count baseline into a text baseline without raising any limit", () => {
  const root = textProject({ "src/a.ts": "// one\n// two\n", "src/b.ts": "// three\n" });
  writeFileSync(path.join(root, "harness-baseline.json"), JSON.stringify({ adopted: ["code-comment"], "code-comment": { "src/a.ts": 2, "src/b.ts": 1 } }));
  assert.equal(check(root).code, 0);
  assert.equal(check(root, "--migrate-text", "code-comment").code, 0);
  assert.deepEqual(baselineOf(root)["code-comment"], { "src/a.ts": { "// one": 1, "// two": 1 }, "src/b.ts": { "// three": 1 } });
  assert.deepEqual(baselineOf(root).adopted, ["code-comment"]);
});

test("migrate-text refuses when a file is over its count or has no allowance", () => {
  const over = textProject({ "src/a.ts": "// one\n// two\n" });
  writeFileSync(path.join(over, "harness-baseline.json"), JSON.stringify({ adopted: ["code-comment"], "code-comment": { "src/a.ts": 1 } }));
  const result = check(over, "--migrate-text", "code-comment");
  assert.equal(result.code, 1);
  assert.match(result.output, /src\/a\.ts: 2 found, 1 allowed/);
  assert.deepEqual(baselineOf(over)["code-comment"], { "src/a.ts": 1 });

  const unlisted = textProject({ "src/a.ts": "// one\n" });
  writeFileSync(path.join(unlisted, "harness-baseline.json"), JSON.stringify({ adopted: ["code-comment"], "code-comment": {} }));
  assert.match(check(unlisted, "--migrate-text", "code-comment").output, /src\/a\.ts: 1 found, none allowed/);
});

test("migrate-text and rewrite only work on rules marked as text baselines", () => {
  const root = textProject({ "src/a.ts": "// one\n" }, [{ ...commentRule, baseline: undefined }]);
  check(root, "--init");
  assert.match(check(root, "--migrate-text", "code-comment").output, /not a text-baseline rule/);
  assert.match(check(root, "--rewrite", "code-comment", "src/a.ts").output, /not a text-baseline rule/);
});

test("rewrite replaces one file's recorded text once, shows the diff, and never raises the count", () => {
  const root = textProject({ "src/a.ts": "// retry is safe\n" });
  check(root, "--init");
  writeFileSync(path.join(root, "src/a.ts"), "// retry is safe because DELETE is guarded\n");
  assert.equal(check(root).code, 1);
  const rewrite = check(root, "--rewrite", "code-comment", "src/a.ts");
  assert.equal(rewrite.code, 0);
  assert.match(rewrite.output, /- \/\/ retry is safe\n/);
  assert.match(rewrite.output, /\+ \/\/ retry is safe because DELETE is guarded/);
  assert.equal(check(root).code, 0);

  writeFileSync(path.join(root, "src/a.ts"), "// first\n// second\n");
  const grown = check(root, "--rewrite", "code-comment", "src/a.ts");
  assert.equal(grown.code, 1);
  assert.match(grown.output, /2 found, 1 allowed\. A rewrite never raises the count/);
});

test("the template marks code-comment, and only code-comment, as a text baseline", () => {
  const template = JSON.parse(readFileSync(new URL("../templates/harness/harness.config.json", import.meta.url), "utf8"));
  assert.deepEqual(template.rules.filter((rule) => rule.baseline === "text").map((rule) => rule.id), ["code-comment"]);
});

test("migrate-text runs once: a text baseline cannot be re-migrated to launder a rewrite", () => {
  const root = textProject({ "src/a.ts": "// retry is safe\n" });
  writeFileSync(path.join(root, "harness-baseline.json"), JSON.stringify({ adopted: ["code-comment"], "code-comment": { "src/a.ts": 1 } }));
  assert.equal(check(root, "--migrate-text", "code-comment").code, 0);
  writeFileSync(path.join(root, "src/a.ts"), "// anything goes\n");
  const again = check(root, "--migrate-text", "code-comment");
  assert.equal(again.code, 1);
  assert.match(again.output, /already records text/);
  assert.deepEqual(baselineOf(root)["code-comment"], { "src/a.ts": { "// retry is safe": 1 } });
  assert.equal(check(root).code, 1);
});

test("an inline comment is recorded by its comment text, so changing only the code on that line passes", () => {
  const root = textProject({ "src/a.ts": "run(); // keep the lease\nconst x = /* inline */ 1;\n" }, [{ ...commentRule, pattern: "\\s//\\s|[\\s(,=]/\\*" }]);
  check(root, "--init");
  assert.deepEqual(baselineOf(root)["code-comment"], { "src/a.ts": { "// keep the lease": 1, "/* inline */": 1 } });
  writeFileSync(path.join(root, "src/a.ts"), "await runAll(); // keep the lease\nconst y = /* inline */ 2;\n");
  assert.equal(check(root).code, 0, check(root).output);
  writeFileSync(path.join(root, "src/a.ts"), "await runAll(); // keep the lease forever\nconst y = /* inline */ 2;\n");
  assert.match(check(root).output, /1 new or rewritten/);
});
