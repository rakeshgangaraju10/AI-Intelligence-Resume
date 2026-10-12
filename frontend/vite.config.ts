import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

// The dev server proxies /api to Django so the SPA and API share one origin:
// session and CSRF cookies then work without cross-site cookie settings.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        "/api": { target: env.VITE_API_PROXY_TARGET || "http://localhost:8000" },
      },
    },
    // `vite preview` (used by the E2E tests) proxies /api the same way.
    preview: {
      proxy: {
        "/api": { target: env.VITE_API_PROXY_TARGET || "http://localhost:8000" },
      },
    },
    test: {
      environment: "jsdom",
      // Playwright specs in e2e/ are run by Playwright, not Vitest.
      include: ["src/**/*.test.{ts,tsx}"],
      setupFiles: ["./src/test/setup.ts"],
      css: false,
      restoreMocks: true,
    },
  };
});
