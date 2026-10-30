import { defineConfig } from "@playwright/test";
import { loadEnv } from "vite";
const localEnv = loadEnv("test", process.cwd(), "RGI_");
export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.RGI_E2E_LOCAL
    ? "**/local.spec.ts"
    : "**/example.spec.ts",
  use: { baseURL: "http://127.0.0.1:5173" },
  webServer: {
    command: process.env.RGI_E2E_LOCAL
      ? "npm run dev -- --port 5173"
      : "npm run demo -- --port 5173",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        launchOptions: {
          executablePath:
            process.env.RGI_BROWSER_EXECUTABLE ||
            localEnv.RGI_BROWSER_EXECUTABLE,
        },
      },
    },
  ],
});
