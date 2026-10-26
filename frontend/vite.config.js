import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on 5173; API calls go to VITE_API_BASE (default the awery-backend on 8200).
export default defineConfig({
  plugins: [react()],
  // allowedHosts:true is needed so Vite accepts requests arriving through a
  // tunnel (trycloudflare.com / devtunnels.ms) instead of "localhost".
  server: { port: 5173, host: true, allowedHosts: true },
});
