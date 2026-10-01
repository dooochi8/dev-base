import { defineConfig } from "@playwright/test";
import path from "node:path";

const output = process.env.BROWSER_EVIDENCE_OUTPUT_DIR;
if (!output) throw new Error("Run node browser-evidence/scripts/run.mjs");

export default defineConfig({
  testDir: "./tests/browser",
  timeout: 30_000,
  retries: 0,
  workers: 1,
  forbidOnly: true,
  outputDir: path.join(output, "raw"),
  reporter: [["list"], ["./browser-evidence/scripts/reporter.mjs"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    browserName: "chromium",
    viewport: { width: 1280, height: 800 },
    video: { mode: "on", size: { width: 1280, height: 800 } },
    screenshot: "only-on-failure",
    trace: "off",
    launchOptions: process.env.BROWSER_EVIDENCE_EXECUTABLE_PATH
      ? { executablePath: process.env.BROWSER_EVIDENCE_EXECUTABLE_PATH }
      : {},
  },
  webServer: {
    // Replace with this project's local app command and readiness endpoint.
    command: "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: false,
    timeout: 90_000,
  },
});
