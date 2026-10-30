import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  testMatch: "**/local.spec.ts",
  workers: 1,
  webServer: {
    command: "../.venv/bin/python ../scripts/e2e_stack.py",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
