const { test, expect } = require("@playwright/test");

test.describe("Player-vs-AI AoS game", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test("starts a battle from the default setup screen", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Age of Sigmar 4th" })
    ).toBeVisible();
    await expect(page.getByText("Choose your opponent")).toBeVisible();

    await page.getByRole("button", { name: /Start battle/ }).click();

    await expect(page.getByText("Your turn", { exact: true })).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();
    await expect(
      page.locator('svg[aria-label^="Battlefield with"]')
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Continue to Hero phase" })
      .click();
    await expect(page.getByText("Your turn", { exact: true })).toBeVisible({
      timeout: 15000,
    });
  });
});
