import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Site estático do Monitor de Licitações. Publicado pelo GitHub Pages em /licitacoes/, por isso os
// caminhos são relativos ("./"): a mesma pasta dist/ funciona em qualquer endereço e em cópia local.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    target: "es2022",
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
