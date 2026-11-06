import { build } from "esbuild";
import { readFile, writeFile } from "node:fs/promises";
const result = await build({
  entryPoints: ["frontend/app.js"],
  bundle: true,
  minify: true,
  supported: { "template-literal": false },
  sourcemap: "external",
  outfile: "aivim/web/static/app.js",
  legalComments: "none",
  footer: { js: "/* Bundled library notices: THIRD_PARTY_LICENSES.txt */" },
  metafile: true,
  logLevel: "info",
});
const packages = new Set();
for (const file of Object.keys(result.metafile.inputs)) {
  const match = /^node_modules\/(@[^/]+\/[^/]+|[^/]+)/.exec(file);
  if (match) packages.add(match[1]);
}
const notices = [
  "Third-party libraries bundled into app.js. AIVim itself is GPL-3.0-only.",
];
for (const name of [...packages].sort()) {
  const directory = "node_modules/" + name;
  const metadata = JSON.parse(
    await readFile(directory + "/package.json", "utf8"),
  );
  let license;
  for (const filename of ["LICENSE", "LICENSE.md", "LICENSE.txt", "license"]) {
    try {
      license = await readFile(directory + "/" + filename, "utf8");
      break;
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
  if (!license)
    throw new Error("Missing license for bundled dependency " + name);
  notices.push(`${name} ${metadata.version}\n${"=".repeat(70)}\n${license}`);
}
await writeFile(
  "aivim/web/static/THIRD_PARTY_LICENSES.txt",
  notices.join("\n\n"),
);
