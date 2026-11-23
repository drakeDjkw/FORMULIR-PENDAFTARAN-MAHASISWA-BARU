import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// 127.0.0.1, not localhost: runserver listens on IPv4 only,
// and Node may try IPv6 (::1) first
const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    // Vite forwards all these requests to Django
    proxy: {
      "/api": backend,
      "/admin": backend, // the admin panel, opened from the front end
      "/static": backend, // admin styles and scripts
      "/media": backend, // uploaded images
    },
  },
});
