import { test, expect } from "@playwright/test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
// Real on-disk SQLite + API + separate worker; explicitly synthetic PDF/provider.
test("local upload → retrieval → persisted fixture run → reload", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Collection library", exact: true })
    .click();
  await page
    .getByLabel("New collection name")
    .fill(`Browser fixture ${Date.now()}`);
  await page.getByRole("button", { name: "Create collection" }).click();
  await page.getByLabel("Paper title").fill("Original synthetic control");
  await page.getByLabel("PDF file").setInputFiles("../fixtures/paper-a.pdf");
  await page.getByRole("button", { name: "Queue ingestion" }).click();
  await expect(page.getByText("ready", { exact: true })).toBeVisible({
    timeout: 120000,
  });
  await page
    .getByRole("button", { name: "Retrieval inspector", exact: true })
    .click();
  await page.getByRole("button", { name: "Search passages" }).click();
  await page
    .getByRole("button", { name: "Inspect original evidence" })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "New investigation", exact: true })
    .click();
  await expect(page.getByLabel("Provider", { exact: true })).toHaveValue(
    "groq",
  );
  await expect(
    page.getByRole("button", { name: "Submit investigation" }),
  ).toBeDisabled();
  await page.getByLabel("Provider", { exact: true }).selectOption("fixture");
  await page.getByRole("button", { name: "Submit investigation" }).click();
  await expect(page.getByText("complete", { exact: true })).toBeVisible({
    timeout: 120000,
  });
  await expect(
    page.getByText("Synthetic fixture run · not real research", {
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Run history", exact: true }).click();
  await page
    .getByRole("button")
    .filter({ hasText: "How should memory retrieval ordering" })
    .click();
  await expect(
    page.getByRole("button", { name: "Export report" }),
  ).toBeEnabled();
});

test("three-paper CLI demo uses actual API and worker with fixture provenance", async () => {
  test.setTimeout(60000);
  const result = await promisify(execFile)(
    ".venv/bin/python",
    [
      "scripts/demo.py",
      "--provider",
      "fixture",
      "--output",
      ".data/e2e-demo-report.md",
    ],
    {
      cwd: "..",
      env: { ...process.env, RGI_OWNER_TOKEN: "" },
      timeout: 45000,
    },
  );
  expect(result.stdout).toContain("Retrieved 3 passages");
  expect(result.stdout).toContain("SYNTHETIC FIXTURE");
  expect(result.stdout).toContain(".data/e2e-demo-report.md");
});
