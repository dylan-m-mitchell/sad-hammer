const { test, expect } = require("@playwright/test");

test.describe("AI turn -> player-roll -> resolve flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("shows turn header immediately and resolves after player rolls", async ({
    page,
  }) => {
    // Upload a roster
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "test-roster.html",
      mimeType: "text/html",
      buffer: Buffer.from("<h1>Test Roster</h1>"),
    });

    // Select player-controlled rolls (if a control exists)
    const playerRadio = page.locator('input[name="roll-mode"][value="player"]');
    const exists = await playerRadio.count();
    if (exists > 0) await playerRadio.check();

    // Trigger create-run
    await page.click("#create-run");

    // Wait for seed log and turn header
    await expect(
      page.locator("text=Created stateless session with seed")
    ).toHaveCount(1, { timeout: 10000 });

    const runBtn = page.locator('button:has-text("Run AI Turn")');
    // Wait for the Run AI Turn button to become enabled (units loaded and ready)
    await expect(runBtn).toBeEnabled({ timeout: 30000 });
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
