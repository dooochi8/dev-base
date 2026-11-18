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

function isTextRule(rule) {
  return rule?.baseline === "text";
}

export function tally(hits = []) {
  const byText = {};
  for (const hit of hits) byText[hit.text] = (byText[hit.text] ?? 0) + 1;
  return byText;
}

export function total(allowance) {
  if (typeof allowance === "number") return allowance;
  return Object.values(allowance ?? {}).reduce((sum, count) => sum + count, 0);
}

function compareFile(rule, file, hits, allowance) {
  if (!isTextRule(rule) || typeof allowance !== "object") {
    const limit = allowance ?? 0;
    if (hits.length > limit) return { regression: { rule, file, hits, limit } };
    return {};
  }
  const actual = tally(hits);
  const excess = Object.entries(actual).filter(([text, count]) => count > (allowance[text] ?? 0)).map(([text, count]) => [text, count - (allowance[text] ?? 0)]);
  if (excess.length === 0) return {};
  const unexpected = new Set(excess.map(([text]) => text));
  const extra = excess.reduce((sum, [, count]) => sum + count, 0);
  return { regression: { rule, file, hits: hits.filter((hit) => unexpected.has(hit.text)), limit: total(allowance), byText: true, extra } };
}

export function compare(config, findings, baseline) {
  const regressions = [];
  const improvements = [];
  for (const rule of config.rules) {
    const actual = findings[rule.id] ?? {};
    const allowed = baseline[rule.id] ?? {};
    for (const [file, hits] of Object.entries(actual)) {
      const { regression } = compareFile(rule, file, hits, allowed[file]);
      if (regression) regressions.push(regression);
    }
    for (const [file, allowance] of Object.entries(allowed)) {
      const hits = actual[file] ?? [];
      if (typeof allowance === "object") {
        const counts = tally(hits);
        const missing = Object.entries(allowance).reduce((sum, [text, limit]) => sum + Math.max(0, limit - (counts[text] ?? 0)), 0);
        if (missing > 0) improvements.push({ rule, file, count: hits.length, limit: total(allowance), missing });
      } else if (hits.length < allowance) {
        improvements.push({ rule, file, count: hits.length, limit: allowance });
      }
    }
  }
  return { regressions, improvements };
}

export function countsOf(findings, config = { rules: [] }) {
  const counts = {};
  for (const [ruleId, files] of Object.entries(findings)) {
    const rule = config.rules.find((candidate) => candidate.id === ruleId);
    for (const [file, hits] of Object.entries(files)) (counts[ruleId] ??= {})[file] = isTextRule(rule) ? tally(hits) : hits.length;
  }
  return counts;
}

export function prune(baseline, findings) {
  const next = baseline.adopted ? { adopted: baseline.adopted } : {};
  for (const [ruleId, files] of Object.entries(baseline)) {
    if (ruleId === "adopted") continue;
    for (const [file, allowance] of Object.entries(files)) {
      const hits = findings[ruleId]?.[file] ?? [];
      if (typeof allowance === "object") {
        const counts = tally(hits);
        const kept = Object.fromEntries(Object.entries(allowance)
          .map(([text, limit]) => [text, Math.min(limit, counts[text] ?? 0)])
          .filter(([, count]) => count > 0));
        if (Object.keys(kept).length > 0) (next[ruleId] ??= {})[file] = kept;
      } else {
        const count = Math.min(allowance, hits.length);
        if (count > 0) (next[ruleId] ??= {})[file] = count;
      }
    }
  }
  return next;
}

export function migrateToText(rule, baseline, findings) {
  const refused = [];
  const files = baseline[rule.id] ?? {};
  const migrated = {};
  for (const [file, hits] of Object.entries(findings[rule.id] ?? {})) {
    if (!Object.hasOwn(files, file)) refused.push(`${file}: ${hits.length} found, none allowed`);
  }
  for (const [file, allowance] of Object.entries(files)) {
    const hits = findings[rule.id]?.[file] ?? [];
    if (hits.length > total(allowance)) refused.push(`${file}: ${hits.length} found, ${total(allowance)} allowed`);
    else if (hits.length > 0) migrated[file] = tally(hits);
  }
  return { refused, migrated };
}

export function rewriteFile(rule, baseline, findings, file) {
  const allowance = baseline[rule.id]?.[file];
  const hits = findings[rule.id]?.[file] ?? [];
  if (typeof allowance !== "object") return { refused: `${file} has no text baseline for ${rule.id}. Run --migrate-text ${rule.id} first.` };
  if (hits.length > total(allowance)) return { refused: `${file}: ${hits.length} found, ${total(allowance)} allowed. A rewrite never raises the count.` };
  return { allowance: tally(hits), before: allowance };
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
    else if (argument === "--migrate-text") {
      options.mode = "migrate-text";
      options.rule = argv[(index += 1)];
    }
    else if (argument === "--rewrite") {
      options.mode = "rewrite";
      options.rule = argv[(index += 1)];
      options.file = argv[(index += 1)];
    }
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
    writeJson(baselinePath, { adopted: config.rules.map((rule) => rule.id).toSorted(), ...countsOf(findings, config) });
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
    const counts = countsOf(findings, config)[options.rule];
    const next = { ...baseline, adopted: [...(baseline.adopted ?? []), options.rule].toSorted() };
    if (counts) next[options.rule] = counts;
    writeJson(baselinePath, next);
    log(`harness: adopted ${options.rule} with ${Object.keys(counts ?? {}).length} files of existing debt.`);
    return 0;
  }

  if (options.mode === "migrate-text" || options.mode === "rewrite") {
    const rule = config.rules.find((candidate) => candidate.id === options.rule);
    if (!isTextRule(rule)) {
      log(`harness: rule ${options.rule} is not a text-baseline rule. Add "baseline": "text" to it in ${options.config} first.`);
      return 1;
    }
    if (options.mode === "migrate-text") {
      const { refused, migrated } = migrateToText(rule, baseline, findings);
      if (refused.length > 0) {
        for (const line of refused) log(`✖ [${rule.id}] ${line}`);
        log(`harness: fix or prune these files first. The baseline never grows.`);
        return 1;
      }
      writeJson(baselinePath, { ...baseline, [rule.id]: migrated });
      log(`harness: recorded the text of ${total(Object.values(migrated).reduce((sum, byText) => sum + total(byText), 0))} ${rule.id} findings in ${Object.keys(migrated).length} files.`);
      return 0;
    }
    const { refused, allowance, before } = rewriteFile(rule, baseline, findings, options.file);
    if (refused) {
      log(`✖ [${rule.id}] ${refused}`);
      return 1;
    }
    const files = { ...baseline[rule.id] };
    if (Object.keys(allowance).length > 0) files[options.file] = allowance;
    else delete files[options.file];
    writeJson(baselinePath, { ...baseline, [rule.id]: files });
    for (const text of Object.keys(before)) if (!Object.hasOwn(allowance, text)) log(`  - ${text}`);
    for (const text of Object.keys(allowance)) if (!Object.hasOwn(before, text)) log(`  + ${text}`);
    log(`harness: rewrote the ${rule.id} text baseline of ${options.file}. Show this diff in the PR for human review.`);
    return 0;
  }

  if (options.mode === "prune") {
    writeJson(baselinePath, prune(baseline, findings));
    log(`harness: pruned ${options.baseline} to the current counts.`);
    return 0;
  }

  const { regressions, improvements } = compare(config, findings, baseline);
  for (const { rule, file, hits, limit, byText, extra } of regressions) {
    if (byText) log(`\n✖ [${rule.id}] ${file}: ${extra} new or rewritten, the baseline allows only its recorded text`);
    else log(`\n✖ [${rule.id}] ${file}: ${hits.length} found, ${limit} allowed by baseline`);
    for (const hit of hits) log(`    ${file}:${hit.line}  ${hit.text}`);
    log(`  → ${rule.message}`);
  }
  for (const { rule, file, count, limit, missing } of improvements) {
    if (missing !== undefined) log(`\n▲ [${rule.id}] ${file}: ${missing} recorded text no longer found`);
    else log(`\n▲ [${rule.id}] ${file}: ${count} found, baseline still allows ${limit}`);
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
