// Playwright E2E configuration (item 77): the smoke suite runs against a
// locally-built Sensei (API + wasm frontend). The CI workflow builds and
// serves the frontend, starts the API with the test database, and runs
// these specs as a real gate.
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8080',
    trace: 'retain-on-failure',
  },
});
