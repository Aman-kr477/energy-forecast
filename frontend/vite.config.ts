import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  build: { chunkSizeWarningLimit: 800 },
  // In dev: proxy /api to the local backend so no CORS issues during development.
  // In production (Vercel): VITE_API_BASE_URL points directly to the Heroku API.
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});