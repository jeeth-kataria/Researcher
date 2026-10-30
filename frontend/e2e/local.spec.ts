import { test, expect } from "@playwright/test";
// Opt in with a real local PostgreSQL/API/worker running in fixture parser/embedder mode.
test.skip(
  !process.env.RGI_E2E_LOCAL,
  "Requires real local PostgreSQL, API and worker",
);
test("local upload → retrieval → persisted fixture run → reload", async ({
  page,
}) => {
  test.skip(
    !process.env.RGI_E2E_LOCAL,
    "Requires real local PostgreSQL, API and worker",
  );
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
  await page.getByRole("button", { name: "Submit investigation" }).click();
  await expect(page.getByText("complete", { exact: true })).toBeVisible({
    timeout: 120000,
  });
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
