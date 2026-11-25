import { copyFile } from "node:fs/promises";
import { build } from "esbuild";

await build({
  entryPoints: { app: "src/main.tsx" },
  outdir: "../services/gateway/app/frontend_dist",
  bundle: true,
  minify: true,
  format: "esm",
  target: "es2022",
  jsx: "automatic",
  define: { "process.env.NODE_ENV": '"production"' },
});
await copyFile("index.html", "../services/gateway/app/frontend_dist/index.html");
