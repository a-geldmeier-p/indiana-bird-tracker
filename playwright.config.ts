import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './playwright-tests',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,

  use: {
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:3838',
    headless: true,
    viewport: {
      width: 1280,
      height: 800
    },
    video: 'on',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure'
  },

  reporter: [
    ['list'],
    ['html', {
      outputFolder: 'playwright-report',
      open: 'never'
    }]
  ]
});