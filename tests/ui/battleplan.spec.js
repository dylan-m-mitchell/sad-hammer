const { test, expect } = require("@playwright/test");

test.describe("Battleplan and Placement Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should allow creating a session and show placement UI", async ({
    page,
  }) => {
    // 1. Upload a file
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "test-roster.html",
      mimeType: "text/html",
      buffer: Buffer.from("<h1>Test Roster</h1>"),
    });

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

    // 3. Trigger upload & parse (create stateless run)
    await page.click("#create-run");

    // 4. Verify a stateless session was created by looking for the seed log entry
    // The frontend logs: "Created stateless session with seed <number>"
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
    // 1. Upload a file without selecting a battleplan (leave it on Random)
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "test-roster.html",
      mimeType: "text/html",
      buffer: Buffer.from("<h1>Test Roster</h1>"),
    });

    // 2. Click create-run without selecting a battleplan
    await page.click("#create-run");

    // 3. Verify stateless session was created (look for seed log entry)
    await expect(
      page.locator("text=Created stateless session with seed")
    ).toHaveCount(1, {
      timeout: 10000,
    });
  });

  test("should show error when no file is selected", async ({ page }) => {
    // When no file is selected the create button should be disabled. Ensure that
    // state rather than attempting to click a disabled control.
    const createBtn = page.locator("#create-run");
    await expect(createBtn).toBeDisabled();
  });
});
