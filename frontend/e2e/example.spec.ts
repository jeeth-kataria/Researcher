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

test("orchestration explains saved handoffs and labels fixture walkthrough", async ({
  page,
}) => {
  await page.goto("/");
  const map = page.getByRole("region", { name: "Agent orchestration" });
  await expect(
    map.getByRole("heading", { name: "Five specialists. One evidence trail." }),
  ).toBeVisible();
  await expect(map.locator(".agent-node")).toHaveCount(6);
  await expect(
    map.locator(".agent-state").filter({ hasText: "Recorded" }),
  ).toHaveCount(6);
  await map
    .getByRole("button", {
      name: "3. Methods analyst: Compare the methods",
      exact: true,
    })
    .click();
  await expect(
    map.getByRole("heading", { name: "Methods analyst", exact: true }),
  ).toBeVisible();
  await map
    .getByRole("button", { name: "Artifact source 1", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await map
    .getByRole("button", { name: "Walk through fixture", exact: true })
    .click();
  await expect(map.getByRole("status")).toContainText("No agents are running");
  await expect(
    map.locator(".agent-state").filter({ hasText: "Awaiting record" }),
  ).toHaveCount(5);
  await expect(
    map.getByRole("button", { name: "Open gap review", exact: true }),
  ).toHaveCount(0);
  await expect(
    map.getByRole("button", { name: "Previous recorded event" }),
  ).toBeDisabled();
  await map.getByRole("button", { name: "Next recorded event" }).click();
  await expect(
    map.getByRole("heading", { name: "Literature specialist", exact: true }),
  ).toBeVisible();
  await map.getByRole("button", { name: "Show all records" }).click();
  await expect(
    map.locator(".agent-state").filter({ hasText: "Recorded" }),
  ).toHaveCount(6);
  await map
    .getByRole("button", { name: "Open gap review", exact: true })
    .click();
  await expect(page.getByText("contradicted", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Orchestration", exact: true }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(() => new Promise(requestAnimationFrame));
  await page.screenshot({
    path: "test-results/orchestration-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(map.locator(".agent-node").first()).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/orchestration-mobile.png",
    fullPage: true,
  });
});

test("stage status follows records and run mode instead of implying completion", async ({
  page,
}) => {
  // Deliberately altered synthetic API response: a UI state test, never a live run.
  await page.route("**/examples/run.json", async (route) => {
    const response = await route.fetch();
    const run = await response.json();
    run.mode = "single";
    run.status = "waiting_for_quota";
    run.events = [
      {
        node: "single",
        kind: "completed",
        data: { summary: "Synthetic saved extraction" },
        duration_ms: null,
        created_at: null,
      },
      {
        node: "review",
        kind: "started",
        data: {},
        duration_ms: null,
        created_at: null,
      },
    ];
    await route.fulfill({ json: run });
  });
  await page.goto("/");
  const map = page.getByRole("region", { name: "Agent orchestration" });
  await expect(
    map.getByRole("heading", { name: "One researcher. Three bounded stages." }),
  ).toBeVisible();
  await expect(map.locator(".agent-node")).toHaveCount(3);
  await expect(
    map.locator(".agent-state").filter({ hasText: "Recorded" }),
  ).toHaveCount(1);
  await expect(
    map.locator(".agent-state").filter({ hasText: "Paused" }),
  ).toHaveCount(1);
  await expect(
    map.locator(".agent-state").filter({ hasText: "Awaiting record" }),
  ).toHaveCount(1);
  await expect(
    map.getByRole("button", { name: "Open gap review", exact: true }),
  ).toHaveCount(0);
  await expect(
    map.getByText("The same researcher self-reviews", { exact: false }),
  ).toBeVisible();
});
