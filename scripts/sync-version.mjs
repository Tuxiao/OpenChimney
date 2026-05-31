import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const checkOnly = process.argv.includes("--check");
const version = readFileSync(resolve(rootDir, "VERSION"), "utf8").trim();

if (!/^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(version)) {
  throw new Error(`Invalid VERSION value: ${version}`);
}

const updates = [
  jsonUpdate("package.json", (data) => {
    data.version = version;
  }),
  jsonUpdate("package-lock.json", (data) => {
    data.version = version;
    data.packages[""].version = version;
    data.packages["apps/web"].version = version;
  }),
  jsonUpdate("apps/web/package.json", (data) => {
    data.version = version;
  }),
  jsonUpdate("apps/web/package-lock.json", (data) => {
    data.version = version;
    data.packages[""].version = version;
  }),
  replaceUpdate("apps/api/pyproject.toml", /^version = ".*"$/m, `version = "${version}"`),
  replaceUpdate("apps/runner/pyproject.toml", /^version = ".*"$/m, `version = "${version}"`),
  replaceUpdate("apps/runner/app/__init__.py", /^__version__ = ".*"$/m, `__version__ = "${version}"`),
  replaceUpdate(".env.example", /^APP_VERSION=.*$/m, `APP_VERSION=${version}`),
  replaceUpdate(".env.docker.example", /^APP_VERSION=.*$/m, `APP_VERSION=${version}`),
  literalUpdate(
    "apps/api/app/version.py",
    `from __future__ import annotations\n\nPROJECT_VERSION = "${version}"\n`
  ),
  literalUpdate(
    "apps/web/src/version.ts",
    `export const APP_VERSION = "${version}";\n`
  )
];

const changed = updates.map((update) => update()).filter(Boolean);
if (checkOnly && changed.length > 0) {
  console.error(`Version metadata is out of sync: ${changed.join(", ")}`);
  process.exit(1);
}

if (changed.length > 0) {
  console.log(`Synced version ${version}: ${changed.join(", ")}`);
} else {
  console.log(`Version metadata already synced at ${version}`);
}

function jsonUpdate(path, mutate) {
  return () => {
    const absolutePath = resolve(rootDir, path);
    const current = readFileSync(absolutePath, "utf8");
    const data = JSON.parse(current);
    mutate(data);
    const next = `${JSON.stringify(data, null, 2)}\n`;
    return writeIfChanged(path, current, next);
  };
}

function replaceUpdate(path, pattern, replacement) {
  return () => {
    const absolutePath = resolve(rootDir, path);
    const current = readFileSync(absolutePath, "utf8");
    if (!pattern.test(current)) {
      throw new Error(`Could not find version field in ${path}`);
    }
    const next = current.replace(pattern, replacement);
    return writeIfChanged(path, current, next);
  };
}

function literalUpdate(path, next) {
  return () => {
    const absolutePath = resolve(rootDir, path);
    let current = "";
    try {
      current = readFileSync(absolutePath, "utf8");
    } catch {
      current = "";
    }
    return writeIfChanged(path, current, next);
  };
}

function writeIfChanged(path, current, next) {
  if (current === next) {
    return "";
  }
  if (!checkOnly) {
    writeFileSync(resolve(rootDir, path), next);
  }
  return path;
}
