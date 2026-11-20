import { defineConfig } from "@playwright/test";

// Follows the installed-Chrome approach in Dnreikronos/cadence#126.
// No browser downloads or fallback launch flags. Intended for GitHub Ubuntu CI.
export default defineConfig({
  testDir: ".",
  forbidOnly: true,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: "list",
  use: {
    channel: "chrome",
    // Playwright defaults to disabling Chromium's sandbox. Fail closed instead.
    launchOptions: { chromiumSandbox: true },
    baseURL: "http://127.0.0.1:4173",
    locale: "en-US",
    timezoneId: "UTC",
    reducedMotion: "reduce",
    serviceWorkers: "block",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: {
    command: "python3 serve.py",
    url: "http://127.0.0.1:4173/vox/",
    reuseExistingServer: false,
    timeout: 10_000,
  },
});
