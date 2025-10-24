const { test, expect } = require("@playwright/test");

test.describe("AI Deployment modal should be scrollable and accessible", () => {
  test("modal body scrolls and Close button remains accessible", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1100, height: 600 });
    await page.goto("/");

    // Upload a dummy roster to trigger session creation and placement modal
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "test-roster.html",
      mimeType: "text/html",
      buffer: Buffer.from("<h1>Test Roster</h1>"),
    });

    // Select first non-random battleplan when available for determinism
    const options = await page
      .locator("#battleplan-select option")
      .count()
      .catch(() => 0);
    if (options > 1) {
      await page.selectOption("#battleplan-select", { index: 1 });
    }

    // Create session
    await page.click("#create-session");

    // Wait for placement modal body to show up
    const modalBody = page.locator("#placement-modal-body");
    await expect(modalBody).toBeVisible({ timeout: 15000 });

    // The modal body should be scrollable (overflow-y auto/scroll)
    const overflowY = await modalBody.evaluate(
      (el) => getComputedStyle(el).overflowY
    );
    expect(["auto", "scroll"]).toContain(overflowY);

    // Ensure the modal content height does not exceed the viewport height by a large margin
    const modalContainer = modalBody.locator(
      "xpath=ancestor::*[@role='dialog']"
    );
    // Our modal container doesn't currently set role=dialog, so fallback to nearest rounded container
    const containerBox = await modalBody
      .locator("xpath=ancestor::*[contains(@class,'rounded-lg')][1]")
      .boundingBox();
    const winH = await page.evaluate(() => window.innerHeight);
    if (containerBox) {
      expect(containerBox.height).toBeLessThanOrEqual(winH * 0.95);
    }

    // Close button should be visible and clickable
    const closeBtn = page.getByRole("button", { name: "Close" });
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();

    // After closing, modal body should disappear
    await expect(modalBody).toBeHidden();
  });
});
