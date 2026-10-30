import { test, expect } from "@playwright/test";
test("read-only example: review, evidence, export and reload", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("Synthetic example · read-only")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "New investigation", exact: true }),
  ).toBeDisabled();
  await page.getByRole("tab", { name: "Gap review" }).click();
  await expect(page.getByText("contradicted", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Source 1" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByText("Text & page fallback", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("dialog").locator("canvas")).toHaveAttribute(
    "width",
    "595",
  );
  await page.screenshot({
    path: "test-results/example-evidence.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export report" }).click();
  expect((await download).suggestedFilename()).toMatch(/research-.*\.md/);
  await page.reload();
  await expect(
    page.getByText(
      "How should memory retrieval ordering be evaluated under distractors?",
      { exact: true },
    ),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/example-desktop.png",
    fullPage: true,
  });
});
test("example matrix, static source inspector and mobile layout", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("tab", { name: "Literature matrix" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await page
    .getByRole("button", { name: "Retrieval inspector", exact: true })
    .click();
  await page.getByRole("button", { name: "Inspect example passages" }).click();
  await expect(
    page.getByRole("button", { name: "Inspect original evidence" }),
  ).toHaveCount(3);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/example-mobile.png",
    fullPage: true,
  });
});
