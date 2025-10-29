const { test, expect } = require("@playwright/test");

test.describe("Battleplan and Placement Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should allow creating a session and show placement UI", async ({
    page,
  }) => {
    // 1. Open upload modal and select a file
    await page.click("#upload-roster");
    const fileInput = await page.locator("#upload-file-modal");
    await fileInput.setInputFiles({
      name: "test-roster.html",
      mimeType: "text/html",
      buffer: Buffer.from("<h1>Test Roster</h1>"),
    });
    // Step 2: choose battleplan and roll mode if desired, then confirm
    // Wait for options step to be available
    await page.click("#upload-next");
    // Select first non-random battleplan when available
    const bpCount = await page
      .locator("#upload-battleplan-select option")
      .count();
    if (bpCount > 1) {
      await page.selectOption("#upload-battleplan-select", { index: 1 });
    }
    await page.click("#upload-confirm");

    // 2. Wait for battleplans to load
    await page.waitForTimeout(1000);

    // Check if there are any battleplan options available
    const battleplanOptions = await page
      .locator("#battleplan-select option")
      .count();

    // If there are battleplans available (more than just the Random option), select the first real one
    if (battleplanOptions > 1) {
      await page.selectOption("#battleplan-select", { index: 1 });
    }

    // After confirming upload (modal), a stateless session should be created.
    // Verify by looking for the seed log entry.
    const seedLog = page.locator("text=Created stateless session with seed");
    await expect(seedLog).toHaveCount(1, { timeout: 10000 });

    // 5. Verify some form of placement UI is shown (check each individually)
    // At least one of these should be visible
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
  });

  test("should allow uploading roster without battleplan selection", async ({
    page,
  }) => {
    // 1. Open upload modal and select a file (leave battleplan as Random)
    await page.click("#upload-roster");
    const fileInput2 = await page.locator("#upload-file-modal");
    await fileInput2.setInputFiles({
      name: "test-roster.html",
      mimeType: "text/html",
      buffer: Buffer.from("<h1>Test Roster</h1>"),
    });
    await page.click("#upload-next");
    await page.click("#upload-confirm");

    // After confirming upload (modal), verify stateless session was created
    await expect(
      page.locator("text=Created stateless session with seed")
    ).toHaveCount(1, {
      timeout: 10000,
    });
  });

  test("should show error when no file is selected", async ({ page }) => {
    // When no file is selected the create button should be disabled. Ensure that
    // state rather than attempting to click a disabled control.
    // Open upload modal and ensure the Upload button is disabled when no file is selected
    await page.click("#upload-roster");
    const uploadConfirm = page.locator("#upload-confirm");
    await expect(uploadConfirm).toBeDisabled();
  });
});
