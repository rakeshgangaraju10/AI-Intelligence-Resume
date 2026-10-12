import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

/**
 * The main user journey, end to end, against the real backend:
 * register -> upload a synthetic PDF -> create a job -> analyse -> download the
 * report -> add a skill -> re-analyse -> compare -> another user can't see it.
 *
 * Expected numbers (see docs/matching-algorithm.md): the fixture resume has
 * Python, Django, PostgreSQL and React. The job requires Python, Django,
 * PostgreSQL and Kubernetes (weight 1 each) and prefers AWS.
 *   first run:  0.8 x 75% + 0.2 x 0% = 60.0
 *   after adding Kubernetes: 0.8 x 100% + 0.2 x 0% = 80.0
 */
const RESUME_PDF = fileURLToPath(new URL("./.generated/e2e-resume.pdf", import.meta.url));
const PASSWORD = "E2e-Correct-Horse-42";

function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

async function register(page: Page, name: string, email: string) {
  await page.goto("/register");
  await page.getByLabel(/^full name/i).fill(name);
  await page.getByLabel(/^email/i).fill(email);
  await page.getByLabel(/^password/i).fill(PASSWORD);
  await page.getByLabel(/^confirm password/i).fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL(/\/dashboard$/);
}

async function runAnalysis(page: Page, jobId: string): Promise<string> {
  await page.goto(`/jobs/${jobId}`);
  await page.getByRole("button", { name: "Run analysis" }).click();
  await page.waitForURL(/\/analyses\/\d+$/);
  await expect(page.getByText("Resume-to-job matching score", { exact: true })).toBeVisible();
  return page.url().split("/").pop()!;
}

test("resume analysis journey", async ({ page }) => {
  let resumeId = "";
  let jobId = "";
  let firstId = "";
  let secondId = "";

  await test.step("register", async () => {
    await register(page, "Riley Synthetic", uniqueEmail("riley"));
  });

  await test.step("upload the synthetic resume", async () => {
    await page.goto("/resumes/upload");
    await page.getByTestId("resume-file-input").setInputFiles(RESUME_PDF);
    await page.getByRole("button", { name: "Upload and analyze" }).click();
    await page.waitForURL(/\/resumes\/[0-9a-f-]{36}$/);
    await expect(page.getByText(/Resume uploaded\. Review what was extracted/)).toBeVisible();
    for (const skill of ["Python", "Django", "PostgreSQL", "React"]) {
      await expect(page.getByRole("button", { name: `Remove ${skill}`, exact: true })).toBeVisible();
    }
    resumeId = page.url().split("/").pop()!;
  });

  await test.step("create a job description", async () => {
    await page.goto("/jobs/new");
    await page.getByLabel(/^job title/i).fill("E2E Backend Developer");
    await page.getByLabel("Suggest skills from the description").uncheck();
    await page.getByLabel(/^required skills/i).fill("Python, Django, PostgreSQL, Kubernetes");
    await page.getByLabel(/^preferred skills/i).fill("AWS");
    await page.getByRole("button", { name: "Save job" }).click();
    await page.waitForURL(/\/jobs\/\d+$/);
    jobId = page.url().split("/").pop()!;
  });

  await test.step("first analysis scores 60.0 with Kubernetes missing", async () => {
    firstId = await runAnalysis(page, jobId);
    await expect(page.getByText(/^60\.0\s*\/\s*100$/)).toBeVisible();
    await expect(page.getByText(/not a probability of being hired/i)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Missing required skills (1)" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Matched required skills (3)" })).toBeVisible();
  });

  await test.step("download the Markdown report", async () => {
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download report" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`careerforge-analysis-${firstId}.md`);
    const text = await readFile(await download.path(), "utf-8");
    expect(text).toContain("## Matching score: 60.0 / 100");
    expect(text).toContain("| Kubernetes | required | 1 | Missing |");
  });

  await test.step("add Kubernetes to the resume and re-run", async () => {
    await page.goto(`/resumes/${resumeId}`);
    await page.getByLabel(/^add a skill/i).fill("Kubernetes");
    await page.getByRole("button", { name: "Add skill" }).click();
    await expect(page.getByRole("button", { name: "Remove Kubernetes", exact: true })).toBeVisible();

    secondId = await runAnalysis(page, jobId);
    expect(secondId).not.toBe(firstId);
    await expect(page.getByText(/^80\.0\s*\/\s*100$/)).toBeVisible();
  });

  await test.step("compare the two analyses from history", async () => {
    await page.goto("/analyses");
    const boxes = page.getByRole("checkbox", { name: /for comparison/i });
    await expect(boxes).toHaveCount(2);
    await boxes.nth(0).check();
    await boxes.nth(1).check();
    await page.getByRole("button", { name: "Compare selected" }).click();
    await page.waitForURL(new RegExp(`/analyses/compare\\?a=${firstId}&b=${secondId}$`));
    await expect(page.getByText("+20.0", { exact: true })).toBeVisible();
    await expect(page.getByRole("row", { name: /Kubernetes/ })).toContainText("Gained");
    await expect(page.getByRole("row", { name: /Python/ })).toContainText("No change");
  });

  await test.step("another user cannot see these analyses", async () => {
    await page.getByRole("button", { name: "Log out" }).click();
    await page.waitForURL(/\/login$/);
    await register(page, "Morgan Synthetic", uniqueEmail("morgan"));

    await page.goto(`/analyses/${firstId}`);
    await expect(page.getByText("Analysis not found", { exact: true })).toBeVisible();
    const api = await page.request.get(`/api/v1/analyses/${firstId}/`);
    expect(api.status()).toBe(404);
    const report = await page.request.get(`/api/v1/analyses/${firstId}/report/`);
    expect(report.status()).toBe(404);
  });
});
