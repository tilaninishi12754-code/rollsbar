import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  expect: { timeout: 8000 },
  reporter: [['list'], ['json', { outputFile: 'test-results-fast/results.json' }]],
  outputDir: './test-results-fast',
  use: {
    baseURL: 'http://127.0.0.1:8081',
    browserName: 'chromium',
    channel: 'chrome',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  projects: [
    { name: 'chrome-desktop', use: { ...devices['Desktop Chrome'], browserName: 'chromium', channel: 'chrome' } },
    { name: 'chrome-mobile', use: { ...devices['iPhone 13'], browserName: 'chromium', channel: 'chrome' } }
  ],
  webServer: {
    command: 'cd .. && python3 -m http.server 8081 --bind 127.0.0.1',
    port: 8081,
    reuseExistingServer: false,
    timeout: 10000
  }
});
