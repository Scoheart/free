import { posix, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, normalizePath } from "vite";

const project = fileURLToPath(new URL("./", import.meta.url));
const web = fileURLToPath(new URL("./web/", import.meta.url));
const dataFiles = new Set(["provider/index.json", "agent/index.json", "vps/index.json"]);

export default defineConfig({
  root: web,
  base: "./",
  plugins: [react(), {
    name: "free-data-feeds",
    configureServer(server) {
      server.middlewares.use((request, _response, next) => {
        const path = request.url?.slice(1).split("?", 1)[0];
        if (path && dataFiles.has(path)) {
          request.url = posix.join("/@fs", normalizePath(resolve(project, path)));
        }
        next();
      });
    },
  }],
  server: { fs: { allow: [project] } },
  build: {
    outDir: "../dist",
    emptyOutDir: true,
    assetsInlineLimit: 0,
    rolldownOptions: {
      input: ["index.html", "provider/index.html", "agent/index.html", "vps/index.html"]
        .map((path) => resolve(web, path)),
      output: {
        assetFileNames: "site-assets/[name]-[hash][extname]",
        entryFileNames: "site-assets/[name]-[hash].js",
        chunkFileNames: "site-assets/[name]-[hash].js",
      },
    },
  },
});
