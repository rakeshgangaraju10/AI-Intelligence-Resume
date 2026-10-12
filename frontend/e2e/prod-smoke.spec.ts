import { expect, test } from "@playwright/test";

/**
 * Runs in the "Production stack" workflow against nginx (docker-compose.prod.yml)
 * over plain HTTP. Login needs HTTPS (Secure cookies), so this only proves the
 * built SPA loads and renders under the production Content-Security-Policy.
 */
test("built SPA renders under the production CSP", async ({ page }) => {
  const violations: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") violations.push(msg.text());
  });
  page.on("pageerror", (err) => violations.push(err.message));

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Explainable match score" })).toBeVisible();

  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();

  await page.goto("/register");
  await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();

  expect(violations.filter((v) => /content security policy|refused to/i.test(v))).toEqual([]);
});
