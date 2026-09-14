import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base is set for GitHub Pages project hosting at /consistent-hash/.
export default defineConfig({
  plugins: [react()],
  base: "/consistent-hash/",
});
