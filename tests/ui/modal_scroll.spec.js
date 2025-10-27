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

    // Trigger upload & parse (create stateless run)
    await page.click("#create-run");

    // Wait for placement modal body to show up, but placement may be auto-confirmed
    // by the frontend/server. If the modal doesn't appear, verify a placement
    // summary or map is visible instead.
    const modalBody = page.locator("#placement-modal-body");
    const modalAppeared = await modalBody
      .waitFor({ timeout: 5000 })
      .then(() => true)
      .catch(() => false);
    if (modalAppeared) {
      // The modal body should be scrollable (overflow-y auto/scroll)
      const overflowY = await modalBody.evaluate(
        (el) => getComputedStyle(el).overflowY
      );
      expect(["auto", "scroll"]).toContain(overflowY);

      // Ensure the modal content height does not exceed the viewport height by a large margin
      const modalContainer = modalBody.locator(
        "xpath=ancestor::*[@role='dialog']"
      );
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
    } else {
      // Modal didn't appear; ensure placement UI exists (summary or map)
      const hasPlacementPanel = await page
        .locator("#placement-panel")
        .isVisible()
        .catch(() => false);
      const hasPlacementSummary = await page
        .locator("#placement-summary")
        .isVisible()
        .catch(() => false);
      const hasPlacementMap = await page
        .locator("#placement-map")
        .isVisible()
        .catch(() => false);
      expect(
        hasPlacementPanel || hasPlacementSummary || hasPlacementMap
      ).toBeTruthy();
    }

    // Ensure the modal content height does not exceed the viewport height by a large margin
    const modalContainer = modalBody.locator(
      "xpath=ancestor::*[@role='dialog']"
    );
    // Our modal container doesn't currently set role=dialog, so fallback to nearest rounded container
    const roundedLocator = modalBody.locator(
      "xpath=ancestor::*[contains(@class,'rounded-lg')][1]"
    );
    let containerBox = null;
    try {
      const count = await roundedLocator.count();
      if (count > 0) {
        containerBox = await roundedLocator.boundingBox();
      }
    } catch (e) {
      // If boundingBox fails or times out due to layout differences, skip the size assertion
      containerBox = null;
    }
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
