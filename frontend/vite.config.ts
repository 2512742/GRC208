import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// During development the API runs on :8000 (uvicorn --reload); Vite proxies /api to it so the
// session and CSRF cookies stay same-origin, exactly as in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  build: { outDir: "dist", sourcemap: false, chunkSizeWarningLimit: 700 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/test/setup.ts"],
    css: false,
  },
});
