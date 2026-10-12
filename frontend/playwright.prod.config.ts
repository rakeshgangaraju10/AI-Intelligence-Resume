import { defineConfig, devices } from "@playwright/test";

// Browser smoke test against an already running production stack (nginx).
export default defineConfig({
  testDir: "./e2e",
  testMatch: "prod-smoke.spec.ts",
  timeout: 30_000,
  retries: 0,
  reporter: process.env.CI ? [["list"], ["github"]] : "list",
  use: { baseURL: process.env.PROD_BASE_URL ?? "http://localhost:8080" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
