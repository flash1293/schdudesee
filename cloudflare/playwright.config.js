import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:8787',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{
    name: 'chromium',
    use: {
      browserName: 'chromium',
      headless: true,
      launchOptions: {
        args: ['--no-sandbox', '--disable-gpu', '--disable-setuid-sandbox'],
      },
    },
  }],
  webServer: {
    command: 'node e2e/test-server.js',
    port: 8787,
    reuseExistingServer: !process.env.CI,
    cwd: process.cwd(),
  },
});
