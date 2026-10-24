import { defineConfig } from '@playwright/test';

// Uses the installed Chrome (channel: 'chrome'); no browser download.
// BB_URL defaults to `vite preview` (proxying /api to the backend); set BB_URL=http://127.0.0.1:8000 once FastAPI serves web/dist.
export default defineConfig({
  testDir: 'e2e',
  timeout: 180_000,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.BB_URL ?? 'http://localhost:4173',
    channel: 'chrome',
    headless: true,
    viewport: { width: 1440, height: 900 },
    locale: 'ar-JO',
  },
});
