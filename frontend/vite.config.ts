import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.LEDGERGUARD_API_URL ?? "http://127.0.0.1:8000",
        changeOrigin: true,
        // The backend sends no SSE body until an event fires, and the default dev proxy
        // holds response headers until the first byte, so EventSource never fires
        // `onopen` and the UI reports the stream as stuck "connecting". Write the
        // upstream status + headers immediately, then stream the body through.
        selfHandleResponse: true,
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes, _req, res) => {
            res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
            res.flushHeaders();
            proxyRes.pipe(res);
          });
        },
      },
    },
  },
});
