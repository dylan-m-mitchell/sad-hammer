import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Single consolidated Vite config. Port set to 8080 to align with Playwright
// preview and the Docker frontend mapping. Proxy API requests to local
// backend at 5000 so dev/preview can reach the Flask server.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8080,
    proxy: {
      "/api": "http://localhost:5000",
      "/battleplans-media": "http://localhost:5000",
    },
  },
  build: {
    outDir: "dist",
  },
});
