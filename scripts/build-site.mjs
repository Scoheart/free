import { existsSync, renameSync } from "node:fs";
import { copyFile, mkdir, mkdtemp, readdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";

const root = fileURLToPath(new URL("../", import.meta.url));
const dist = join(root, "dist");
const assetsDir = "site-assets";
const feeds = [
  { json: "provider/index.json", valid: Array.isArray },
  { json: "agent/index.json", valid: Array.isArray },
  { json: "vps/index.json", valid: (value) => value && typeof value === "object" && !Array.isArray(value) },
];
const legacyScripts = ["data.js", "vps-data.js"];

async function readFeed(feed) {
  const raw = await readFile(join(root, feed.json));
  const value = JSON.parse(raw.toString("utf8"));
  if (!feed.valid(value)) throw new Error("Unexpected JSON shape in " + feed.json);
  return { ...feed, raw, value };
}

async function mirrorFile(output, file) {
  const destination = join(root, file);
  const temporary = destination + "." + randomUUID() + ".tmp";
  await mkdir(dirname(destination), { recursive: true });
  try {
    await copyFile(join(output, file), temporary);
    await rename(temporary, destination);
  } finally {
    await rm(temporary, { force: true });
  }
}

async function mirrorPages(output) {
  const assets = await readdir(join(output, assetsDir), { withFileTypes: true });
  const names = assets.filter((asset) => asset.isFile()).map((asset) => asset.name);
  if (!names.length) throw new Error("Vite generated no site assets");

  const entries = await readdir(output, { recursive: true, withFileTypes: true });
  const pages = entries.filter((entry) => entry.isFile() && entry.name === "index.html")
    .map((entry) => relative(output, join(entry.parentPath, entry.name)));
  if (!pages.includes("index.html")) throw new Error("Vite generated no home page");

  // Install bundles before HTML points at them. The JSON feeds are already in the page folders.
  await Promise.all(names.map((name) => mirrorFile(output, join(assetsDir, name))));
  await Promise.all(legacyScripts.map((script) => mirrorFile(output, script)));
  await Promise.all(pages.map((page) => mirrorFile(output, page)));

  const previous = await readdir(join(root, assetsDir), { withFileTypes: true });
  const current = new Set(names);
  for (const asset of previous) {
    if (asset.isFile() && /^[\w-]+-[\w-]{8,}\.(?:js|css)$/.test(asset.name) && !current.has(asset.name)) {
      await rm(join(root, assetsDir, asset.name), { force: true });
    }
  }
}

function installOutput(output, previous) {
  try {
    renameSync(dist, previous);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  try {
    renameSync(output, dist);
  } catch (error) {
    if (existsSync(previous) && !existsSync(dist)) {
      try {
        renameSync(previous, dist);
      } catch (restoreError) {
        throw new AggregateError([error, restoreError], "Previous output is available at " + previous);
      }
    }
    throw error;
  }
}

const snapshots = await Promise.all(feeds.map(readFeed));
const scratch = await mkdtemp(join(root, ".build-site-"));
const output = join(scratch, "output");
const previous = join(scratch, "previous-dist");
let installed = false;

try {
  await build({ configFile: join(root, "vite.config.ts"), build: { outDir: output } });
  await Promise.all(snapshots.map(async ({ json, raw }) => {
    if (!(await readFile(join(root, json))).equals(raw)) throw new Error(json + " changed during the build");
    await writeFile(join(output, json), raw);
  }));
  const [provider, agent, vps] = snapshots;
  await Promise.all([
    writeFile(join(output, "data.js"), "const ITEMS = " + JSON.stringify(provider.value.concat(agent.value)) + ";\n"),
    writeFile(join(output, "vps-data.js"), "const VPS = " + JSON.stringify(vps.value) + ";\n"),
  ]);
  await copyFile(join(root, ".nojekyll"), join(output, ".nojekyll"));
  await readFile(join(output, "_redirects"));

  if (process.argv.includes("--pages")) {
    await mirrorPages(output);
    console.log("GitHub Pages 发布文件已更新。");
  }
  installOutput(output, previous);
  installed = true;
  console.log("部署目录 dist/");
} finally {
  if (installed || !existsSync(previous)) await rm(scratch, { recursive: true, force: true });
}
