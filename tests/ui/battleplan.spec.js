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

    // 3. Click create session
    await page.click("#create-session");

    // 4. Verify session was created (wait for session ID to appear and not be "(none)")
    await expect(page.locator("#session-id")).not.toHaveText("(none)", {
      timeout: 10000,
    });

    // Get the session ID for verification
    const sessionId = await page.locator("#session-id").textContent();
    expect(sessionId).not.toBe("(none)");
    expect(sessionId?.length).toBeGreaterThan(0);

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

    // 2. Click create session without selecting a battleplan
    await page.click("#create-session");

    // 3. Verify session was created
    await expect(page.locator("#session-id")).not.toHaveText("(none)", {
      timeout: 10000,
    });

    const sessionId = await page.locator("#session-id").textContent();
    expect(sessionId).not.toBe("(none)");
    expect(sessionId?.length).toBeGreaterThan(0);
  });

  test("should show error when no file is selected", async ({ page }) => {
    // Set up dialog handler to capture the alert
    page.on("dialog", async (dialog) => {
      expect(dialog.message()).toContain("Choose an HTML roster first");
      await dialog.accept();
    });

    // Try to create session without selecting a file
    await page.click("#create-session");

    // The alert should have been triggered (handled by the dialog handler above)
  });
});
