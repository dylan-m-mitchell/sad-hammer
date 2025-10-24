const { defineConfig, devices } = require("@playwright/test");
const baseURL = process.env.BASE_URL || "http://localhost:8080";

module.exports = defineConfig({
  testDir: "./tests/ui",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL,
    trace: "on-first-retry",
  },

  /* We expect the dev server to already be running via docker compose */
  /* If you need to start it automatically, run: docker compose up --build */
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
