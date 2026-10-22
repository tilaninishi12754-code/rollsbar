import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';
export default defineConfig({
  testDir: '.', testMatch: 'gate.spec.mjs', workers: 1, retries: 0,
  timeout: 30000,
  updateSnapshots: process.env.ROLLSBAR_BASELINE === '1' ? 'all' : 'none',
  snapshotPathTemplate: '{testDir}/baselines/{projectName}/{arg}{ext}',
  outputDir: '../visual-results/normal/results',
  reporter: [['dot'], ['html', { outputFolder: resolve('qa/visual-results/normal/report'), open:'never' }], ['json', {outputFile:resolve('qa/visual-results/normal/results.json')}]],
  expect: { timeout: 5000, toHaveScreenshot: { animations:'disabled', caret:'hide', scale:'css', maxDiffPixels:0 } },
  use: { browserName:'chromium', headless:true, deviceScaleFactor:1, locale:'ru-RU', timezoneId:'Europe/Moscow', colorScheme:'light', reducedMotion:'reduce', serviceWorkers:'block', trace:'retain-on-failure' },
  projects: [1440,1051,1050,1024,701,700,390,320].map(width=>({name:`w${width}`,use:{viewport:{width,height:900}}}))
});
