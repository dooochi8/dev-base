import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const latest = JSON.parse(await readFile(path.join(root, ".artifacts/browser-evidence/latest.json"), "utf8"));
const run = path.resolve(latest.directory);
const relativeRun = path.relative(path.join(root, ".artifacts/browser-evidence"), run);
if (relativeRun.startsWith("..") || path.isAbsolute(relativeRun)) throw new Error("Unexpected evidence run path");
const manifest = JSON.parse(await readFile(path.join(run, "manifest.json"), "utf8"));
// upload-artifact excludes hidden directories by default; keep this allowlisted staging path visible.
const output = path.join(root, "tmp/browser-evidence-upload");
await mkdir(path.join(output, "assets"), { recursive: true });
for (const test of manifest.tests) {
  for (const asset of test.assets) {
    if (!/^assets\/[a-f0-9]{16}-\d+-\d+\.(webm|mp4|png)$/u.test(asset.file)) throw new Error("Unexpected evidence media path");
    await copyFile(path.join(run, asset.file), path.join(output, asset.file));
  }
}
await writeFile(path.join(output, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`Staged ${manifest.status} evidence. Raw output and logs were excluded.`);
