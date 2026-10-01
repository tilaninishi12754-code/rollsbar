import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  expect: { timeout: 8000 },
  reporter: [['list'], ['json', { outputFile: 'test-results/results.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    { name: 'chromium-desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'webkit-iphone13', use: { ...devices['iPhone 13'], browserName: 'webkit' } }
  ],
  webServer: {
    command: 'cd .. && python3 -m http.server 8080 --bind 127.0.0.1',
    port: 8080,
    reuseExistingServer: false,
    timeout: 10000
  }
});
