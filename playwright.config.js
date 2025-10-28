const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tests/ui",
  use: {
    // The application under test listens on port 8080
    baseURL: "http://localhost:8080",
    headless: true,
    viewport: { width: 1200, height: 800 },
    ignoreHTTPSErrors: true,
    actionTimeout: 10000,
    navigationTimeout: 20000,
  },
});
