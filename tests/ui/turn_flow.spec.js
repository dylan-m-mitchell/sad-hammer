const { test, expect } = require("@playwright/test");

test.describe("AI turn -> player-roll -> resolve flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("shows turn header immediately and resolves after player rolls", async ({
    page,
  }) => {
    // Open upload modal and upload a roster
    await page.click("#upload-roster");
    const fileInput = await page.locator("#upload-file-modal");
    await fileInput.setInputFiles({
      name: "test-roster.html",
      mimeType: "text/html",
      buffer: Buffer.from("<h1>Test Roster</h1>"),
    });
    await page.click("#upload-confirm");

    // Select player-controlled rolls (if a control exists)
    const playerRadio = page.locator('input[name="roll-mode"][value="player"]');
    const exists = await playerRadio.count();
    if (exists > 0) await playerRadio.check();

    // After confirming upload (modal), seed and units should be available.

    // Wait for seed log and turn header
    await expect(
      page.locator("text=Created stateless session with seed")
    ).toHaveCount(1, { timeout: 10000 });

    // Ensure units have been loaded into the UI (the app logs this explicitly)
    // The frontend logs: "Loaded <n> AI units" — wait for that pattern.
    await expect(page.locator("text=/Loaded \\d+ AI units/")).toHaveCount(1, {
      timeout: 10000,
    });

    // Target the desktop Run AI Turn button by id to avoid matching the mobile
    // fixed bottom button which exists concurrently in the DOM.
    const desktop = page.locator("#run-ai-turn");
    const mobile = page.locator("#run-ai-turn-mobile");

    // Wait up to 30s for either the desktop or mobile Run button to become enabled.
    let runBtn = null;
    for (let i = 0; i < 60; i++) {
      if (await desktop.isEnabled().catch(() => false)) {
        runBtn = desktop;
        break;
      }
      if (await mobile.isEnabled().catch(() => false)) {
        runBtn = mobile;
        break;
      }
      await page.waitForTimeout(500);
    }
    if (!runBtn) throw new Error("Run AI Turn button did not become enabled");
    await runBtn.click();

    // The turn header should be present immediately
    const turnHeader = page.locator("text=/=== AI Turn \\d+ ===/");
    await expect(turnHeader).toHaveCount(1);

    // A player roll request should appear either as a log entry or as the roll modal
    const rollRequestLog = page.locator("text=PLAYER ROLL REQUEST");
    const modalTitle = page.locator("text=Enter Dice Results");
    if ((await rollRequestLog.count()) > 0) {
      await expect(rollRequestLog.first()).toBeVisible({ timeout: 5000 });
    } else {
      await expect(modalTitle).toBeVisible({ timeout: 5000 });
    }

    // If a roll modal appears, fill it in with '4's for each required input and submit
    const modal = page
      .locator("text=Enter Dice Results")
      .locator("xpath=ancestor::div[1]");
    const modalShown =
      (await modal.count()) > 0 && (await modal.isVisible()).catch(() => false);
    if (modalShown) {
      // fill numeric inputs
      const inputs = modal.locator('input[type="number"]');
      const n = await inputs.count();
      for (let i = 0; i < n; i++) await inputs.nth(i).fill("4");
      // submit
      await modal.locator('button:has-text("Submit")').click();
    } else {
      // If no modal, try to find small input fields in the page (fallback)
      const inputs = page.locator('input[type="number"]');
      const n = await inputs.count();
      for (let i = 0; i < n; i++) await inputs.nth(i).fill("4");
      // click any resolve button
      const resolveBtn = page.locator('button:has-text("Resolve")');
      if ((await resolveBtn.count()) > 0) await resolveBtn.first().click();
    }

    // After resolving, ensure events for that same turn are printed and the next turn header appears
    // After resolving, ensure events for that same turn are printed and the next turn header appears
    await page
      .locator("text=/=== AI Turn \\d+ ===/")
      .nth(1)
      .waitFor({ state: "visible", timeout: 5000 });
  });
});
