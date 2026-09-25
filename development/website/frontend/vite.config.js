import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on the LAN, not just localhost: players join from their own
    // phones on the same Wi-Fi as the host machine.
    host: true,
  },
});
