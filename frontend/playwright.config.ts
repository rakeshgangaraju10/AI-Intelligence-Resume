import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the real stack: Django (dev settings, PostgreSQL)
 * plus the Vite dev server, whose /api proxy keeps the app and API on one origin.
 *
 * Prerequisites (see README "End-to-end tests"):
 *   - PostgreSQL running and `python manage.py migrate` done
 *   - the synthetic fixture: python scripts/make_e2e_resume_pdf.py frontend/e2e/.generated/e2e-resume.pdf
 * Playwright starts both servers unless they are already running locally.
 */
const PYTHON = process.env.E2E_PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  testIgnore: "prod-smoke.spec.ts", // run by playwright.prod.config.ts
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  // "github" turns failures into annotations visible on the public run page.
  reporter: process.env.CI ? [["list"], ["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${PYTHON} manage.py runserver 127.0.0.1:8000 --noreload`,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/v1/health/",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      stdout: "pipe",
    },
    {
      // Production build + `vite preview` (same /api proxy as dev). The dev server
      // reloads the page while it optimises dependencies on first visit, which
      // interrupted typing in CI.
      command: "npx vite build && npx vite preview --host 127.0.0.1 --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      // Node may resolve "localhost" to ::1 while Django listens on 127.0.0.1.
      env: { VITE_API_PROXY_TARGET: "http://127.0.0.1:8000" },
    },
  ],
});
