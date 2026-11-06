// Bundles the card into the integration package, which serves it (docs/SPEC.md §2).
// The bundle is committed so that a HACS install needs no build step;
// `--check` (CI) fails when the committed bundle is out of date.
import { build } from "esbuild";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const outfile = fileURLToPath(
  new URL(
    "../custom_components/energy_cost_stats/frontend/energy-cost-stats-card.js",
    import.meta.url,
  ),
);
const check = process.argv.includes("--check");

const result = await build({
  entryPoints: [fileURLToPath(new URL("src/index.ts", import.meta.url))],
  bundle: true,
  format: "esm",
  target: "es2022",
  minify: true,
  legalComments: "none",
  charset: "utf8",
  write: false,
  logLevel: "warning",
});
const code = result.outputFiles[0].text;

if (check) {
  let current = "";
  try {
    current = readFileSync(outfile, "utf8");
  } catch {
    // Missing bundle counts as out of date.
  }
  if (current !== code) {
    console.error(
      "The committed card bundle is out of date: run `npm run build` in frontend/ and commit it.",
    );
    process.exit(1);
  }
  console.log("Card bundle is up to date.");
} else {
  writeFileSync(outfile, code);
  console.log(`Wrote ${outfile} (${code.length} bytes)`);
}
