#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const IGNORED_DIRECTORIES = new Set([".git", "node_modules", "dist", "build", "coverage", ".vite", ".react-router", ".wrangler"]);

export function globToRegExp(glob) {
  let source = "";
  for (let index = 0; index < glob.length; index += 1) {
    const char = glob[index];
    if (char === "*" && glob[index + 1] === "*") {
      const followedBySlash = glob[index + 2] === "/";
      source += followedBySlash ? "(?:.*/)?" : ".*";
      index += followedBySlash ? 2 : 1;
    } else if (char === "*") {
      source += "[^/]*";
    } else if (char === "?") {
      source += "[^/]";
    } else {
      source += char.replace(/[.+^${}()|[\]\\]/g, "\\$&");
    }
  }
  return new RegExp(`^${source}$`);
}

function matchesAny(file, globs = []) {
  return globs.some((glob) => globToRegExp(glob).test(file));
}

function walk(root, directory, files) {
  for (const entry of readdirSync(path.join(root, directory), { withFileTypes: true })) {
    if (IGNORED_DIRECTORIES.has(entry.name)) continue;
    const relative = directory ? `${directory}/${entry.name}` : entry.name;
    if (entry.isDirectory()) walk(root, relative, files);
    else if (entry.isFile()) files.push(relative);
  }
}

export function listFiles(root, config) {
  const files = [];
  walk(root, "", files);
  return files
    .filter((file) => matchesAny(file, config.include))
    .filter((file) => !matchesAny(file, config.exclude))
    .toSorted();
}

function occurrences(rule) {
  const flags = rule.flags ?? "";
  const pattern = new RegExp(rule.pattern, flags.includes("g") ? flags : `${flags}g`);
  return (line) => [...line.matchAll(pattern)].filter((match) => match[0].length > 0).length;
}

export function scan(root, config) {
  const findings = {};
  for (const file of listFiles(root, config)) {
    const lines = readFileSync(path.join(root, file), "utf8").split("\n");
    for (const rule of config.rules) {
      if (rule.include && !matchesAny(file, rule.include)) continue;
      if (matchesAny(file, rule.allow) || matchesAny(file, rule.exclude)) continue;
      const count = occurrences(rule);
      const hits = [];
      lines.forEach((line, index) => {
        const matches = count(line);
        for (let hit = 0; hit < matches; hit += 1) hits.push({ line: index + 1, text: line.trim() });
      });
      if (hits.length > 0) (findings[rule.id] ??= {})[file] = hits;
    }
  }
  return findings;
}

export function compare(config, findings, baseline) {
  const regressions = [];
  const improvements = [];
  for (const rule of config.rules) {
    const actual = findings[rule.id] ?? {};
    const allowed = baseline[rule.id] ?? {};
    for (const [file, hits] of Object.entries(actual)) {
      const limit = allowed[file] ?? 0;
      if (hits.length > limit) regressions.push({ rule, file, hits, limit });
    }
    for (const [file, limit] of Object.entries(allowed)) {
      const count = actual[file]?.length ?? 0;
      if (count < limit) improvements.push({ rule, file, count, limit });
    }
  }
  return { regressions, improvements };
}

export function countsOf(findings) {
  const counts = {};
  for (const [ruleId, files] of Object.entries(findings)) {
    for (const [file, hits] of Object.entries(files)) (counts[ruleId] ??= {})[file] = hits.length;
  }
  return counts;
}

export function prune(baseline, findings) {
  const actual = countsOf(findings);
  const next = baseline.adopted ? { adopted: baseline.adopted } : {};
  for (const [ruleId, files] of Object.entries(baseline)) {
    if (ruleId === "adopted") continue;
    for (const [file, limit] of Object.entries(files)) {
      const count = Math.min(limit, actual[ruleId]?.[file] ?? 0);
      if (count > 0) (next[ruleId] ??= {})[file] = count;
    }
  }
  return next;
}

export function selfTest(config) {
  const failures = [];
  for (const rule of config.rules) {
    const { bad = [], good = [] } = rule.examples ?? {};
    if (bad.length === 0 || good.length === 0) {
      failures.push(`[${rule.id}] needs examples.bad and examples.good: one line the rule must catch, one correct line it must not`);
      continue;
    }
    const count = occurrences(rule);
    for (const line of bad) if (count(line) === 0) failures.push(`[${rule.id}] misses bad example: ${line}`);
    for (const line of good) if (count(line) > 0) failures.push(`[${rule.id}] flags good example: ${line}`);
  }
  return failures;
}

function sortKeys(value) {
  if (Array.isArray(value) || value === null || typeof value !== "object") return value;
  return Object.fromEntries(Object.keys(value).toSorted().map((key) => [key, sortKeys(value[key])]));
}

function writeJson(file, value) {
  writeFileSync(file, `${JSON.stringify(sortKeys(value), null, 2)}\n`);
}

function parseArguments(argv) {
  const options = { root: process.cwd(), config: "harness.config.json", baseline: "harness-baseline.json", mode: "check" };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--root") options.root = path.resolve(argv[(index += 1)]);
    else if (argument === "--config") options.config = argv[(index += 1)];
    else if (argument === "--baseline") options.baseline = argv[(index += 1)];
    else if (argument === "--init") options.mode = "init";
    else if (argument === "--prune") options.mode = "prune";
    else if (argument === "--adopt") {
      options.mode = "adopt";
      options.rule = argv[(index += 1)];
    }
    else if (argument === "--self-test") options.mode = "self-test";
    else throw new Error(`Unknown argument: ${argument}`);
  }
  return options;
}

export function run(argv, log = console.log) {
  const options = parseArguments(argv);
  const configPath = path.resolve(options.root, options.config);
  const baselinePath = path.resolve(options.root, options.baseline);
  const config = JSON.parse(readFileSync(configPath, "utf8"));

  if (options.mode === "self-test") {
    const failures = selfTest(config);
    for (const failure of failures) log(`✖ ${failure}`);
    if (failures.length > 0) return 1;
    log(`harness: ${config.rules.length} rules caught their bad examples and spared their good ones.`);
    return 0;
  }

  const findings = scan(options.root, config);

  if (options.mode === "init") {
    if (existsSync(baselinePath)) {
      log(`harness: ${options.baseline} already exists. Use --prune to shrink it; the baseline never grows.`);
      return 1;
    }
    writeJson(baselinePath, { adopted: config.rules.map((rule) => rule.id).toSorted(), ...countsOf(findings) });
    log(`harness: wrote ${options.baseline}.`);
    return 0;
  }

  const baseline = existsSync(baselinePath) ? JSON.parse(readFileSync(baselinePath, "utf8")) : {};

  if (options.mode === "adopt") {
    if (!config.rules.some((rule) => rule.id === options.rule)) {
      log(`harness: rule ${options.rule} is not in ${options.config}.`);
      return 1;
    }
    if (Object.hasOwn(baseline, options.rule) || baseline.adopted?.includes(options.rule)) {
      log(`harness: rule ${options.rule} is already adopted. The baseline never grows.`);
      return 1;
    }
    const counts = countsOf(findings)[options.rule];
    const next = { ...baseline, adopted: [...(baseline.adopted ?? []), options.rule].toSorted() };
    if (counts) next[options.rule] = counts;
    writeJson(baselinePath, next);
    log(`harness: adopted ${options.rule} with ${Object.keys(counts ?? {}).length} files of existing debt.`);
    return 0;
  }

  if (options.mode === "prune") {
    writeJson(baselinePath, prune(baseline, findings));
    log(`harness: pruned ${options.baseline} to the current counts.`);
    return 0;
  }

  const { regressions, improvements } = compare(config, findings, baseline);
  for (const { rule, file, hits, limit } of regressions) {
    log(`\n✖ [${rule.id}] ${file}: ${hits.length} found, ${limit} allowed by baseline`);
    for (const hit of hits) log(`    ${file}:${hit.line}  ${hit.text}`);
    log(`  → ${rule.message}`);
  }
  for (const { rule, file, count, limit } of improvements) {
    log(`\n▲ [${rule.id}] ${file}: ${count} found, baseline still allows ${limit}`);
  }
  if (improvements.length > 0) {
    log(`\nRun the harness check with --prune to lock in the improvement.`);
  }
  if (regressions.length > 0 || improvements.length > 0) return 1;
  log(`harness: ${config.rules.length} rules passed.`);
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = run(process.argv.slice(2));
}
