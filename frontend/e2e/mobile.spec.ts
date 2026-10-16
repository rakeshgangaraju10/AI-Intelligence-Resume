import { fileURLToPath } from "node:url";

import { devices, expect, test, type Page } from "@playwright/test";

/**
 * Phone layout check: every main page must fit a phone screen without sideways
 * scrolling. Uses a Pixel 5 profile (393 px wide, touch, mobile viewport) in
 * Chromium and saves a full-page screenshot of each page.
 */
const RESUME_PDF = fileURLToPath(new URL("./.generated/e2e-resume.pdf", import.meta.url));
const SHOTS = fileURLToPath(new URL("./.generated/screenshots/", import.meta.url));
const PASSWORD = "E2e-Correct-Horse-42";

const PIXEL_5 = devices["Pixel 5"];
test.use({
  viewport: PIXEL_5.viewport,
  userAgent: PIXEL_5.userAgent,
  deviceScaleFactor: PIXEL_5.deviceScaleFactor,
  isMobile: PIXEL_5.isMobile,
  hasTouch: PIXEL_5.hasTouch,
});

/** Fails with the elements that stick out past the right edge of the screen. */
async function expectFitsScreen(page: Page, name: string) {
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: `${SHOTS}mobile-${name}.png`, fullPage: true });
  const overflow = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    const scrollWidth = document.documentElement.scrollWidth;
    const offenders: string[] = [];
    if (scrollWidth > width + 1) {
      for (const el of Array.from(document.body.querySelectorAll<HTMLElement>("*"))) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.right > width + 1) {
          const cls = typeof el.className === "string" ? el.className.split(" ").slice(0, 4).join(".") : "";
          offenders.push(`${el.tagName.toLowerCase()}${cls ? "." + cls : ""} (right ${Math.round(rect.right)}px)`);
          if (offenders.length >= 5) break;
        }
      }
    }
    return { width, scrollWidth, offenders };
  });
  expect.soft(
    overflow.scrollWidth,
    `${name}: page is ${overflow.scrollWidth}px wide on a ${overflow.width}px screen. Sticking out: ${overflow.offenders.join(", ")}`,
  ).toBeLessThanOrEqual(overflow.width + 1);
}

test("every page fits a phone screen", async ({ page }) => {
  for (const [path, name] of [
    ["/", "landing"],
    ["/login", "login"],
    ["/register", "register"],
    ["/forgot-password", "forgot-password"],
  ] as const) {
    await page.goto(path);
    await expectFitsScreen(page, name);
  }

  // Sign up, then fill the app with synthetic data.
  await page.goto("/register");
  await page.getByLabel(/^full name/i).fill("Pat Phone");
  await page.getByLabel(/^email/i).fill(`pat-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`);
  await page.getByLabel(/^password/i).fill(PASSWORD);
  await page.getByLabel(/^confirm password/i).fill(PASSWORD);
  await page.getByLabel(/^college name/i).fill("Example Institute of Technology");
  await page.getByLabel(/^year of passing out/i).selectOption("2025");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL(/\/dashboard$/);
  await expectFitsScreen(page, "dashboard-empty");

  await page.goto("/resumes/upload");
  await expectFitsScreen(page, "upload");
  await page.getByTestId("resume-file-input").setInputFiles(RESUME_PDF);
  await page.getByRole("button", { name: "Upload and analyze" }).click();
  await page.waitForURL(/\/resumes\/[0-9a-f-]{36}$/);
  await expectFitsScreen(page, "resume-review");

  await page.goto("/jobs/new");
  await expectFitsScreen(page, "job-new");
  await page.getByLabel(/^job title/i).fill("Backend Developer (Python, Django, PostgreSQL) – Graduate Programme");
  await page.getByLabel(/^required skills/i).fill("Python, Django, PostgreSQL, Kubernetes");
  await page.getByLabel(/^preferred skills/i).fill("AWS");
  await page.getByRole("button", { name: "Save job" }).click();
  await page.waitForURL(/\/jobs\/\d+$/);
  const jobId = page.url().split("/").pop()!;
  await expectFitsScreen(page, "job-detail");

  const analysisIds: string[] = [];
  for (let i = 0; i < 2; i++) {
    await page.goto(`/jobs/${jobId}`);
    await page.getByRole("button", { name: "Run analysis" }).click();
    await page.waitForURL(/\/analyses\/\d+$/);
    await expect(page.getByText("Resume-to-job matching score", { exact: true })).toBeVisible();
    analysisIds.push(page.url().split("/").pop()!);
  }
  await expectFitsScreen(page, "analysis");

  await page.goto(`/analyses/compare?a=${analysisIds[0]}&b=${analysisIds[1]}`);
  await expect(page.getByRole("heading", { name: "Compare analyses" })).toBeVisible();
  await expectFitsScreen(page, "compare");

  for (const [path, name] of [
    ["/dashboard", "dashboard"],
    ["/resumes", "resumes"],
    ["/jobs", "jobs"],
    ["/analyses", "history"],
    ["/settings", "settings"],
  ] as const) {
    await page.goto(path);
    await expectFitsScreen(page, name);
  }

  // The menu button replaces the top navigation on phones.
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.locator("#mobile-nav").getByRole("link", { name: "Jobs" })).toBeVisible();
  await expectFitsScreen(page, "menu-open");
});
