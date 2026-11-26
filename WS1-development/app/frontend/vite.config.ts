import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

/**
 * Writes dist/sw.js from sw.template.js with the list of built files to precache and a
 * version derived from their names, so every deploy gets a new worker and old caches are
 * deleted. Hand-written instead of a plugin library, so the whole policy is readable.
 */
function serviceWorker(): Plugin {
  return {
    name: "risktrack-service-worker",
    apply: "build",
    generateBundle(_options, bundle) {
      const built = Object.keys(bundle).filter((f) => /\.(js|css)$/.test(f) && f.startsWith("assets/"));
      const shell = ["/", "/index.html", "/theme-init.js", "/manifest.webmanifest", "/favicon.svg?v=2", "/icons/icon-192.png?v=2", "/icons/icon-512.png?v=2", "/icons/maskable-512.png?v=2", "/icons/apple-touch-icon.png?v=2"];
      const precache = [...shell, ...built.map((f) => `/${f}`)];
      const version = createHash("sha256").update(precache.join("|")).digest("hex").slice(0, 12);
      const source = readFileSync(new URL("./sw.template.js", import.meta.url), "utf8")
        .replace("__VERSION__", version)
        .replace("__PRECACHE__", JSON.stringify(precache, null, 2));
      this.emitFile({ type: "asset", fileName: "sw.js", source });
    },
  };
}

// During development the API runs on :8000 (uvicorn --reload); Vite proxies /api to it so the
// session and CSRF cookies stay same-origin, exactly as in production.
export default defineConfig({
  plugins: [react(), serviceWorker()],
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
