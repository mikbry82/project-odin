import { spawn } from "node:child_process";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const executable = path.join(
  root,
  "frontend",
  "release-v1.2.1",
  "win-unpacked",
  "resources",
  "backend",
  "project-odin-backend.exe",
);
const validationDirectory = path.join(root, ".tmp-packaged-validation");
const databasePath = path.join(validationDirectory, "project-odin.db").replaceAll("\\", "/");
const backend = spawn(executable, [], {
  env: {
    ...process.env,
    APPDATA: validationDirectory,
    DATABASE_URL: `sqlite+aiosqlite:///${databasePath}`,
  },
  stdio: ["pipe", "ignore", "ignore"],
  windowsHide: true,
});

async function waitForHealth() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch("http://127.0.0.1:8000/health");
      if (response.ok) return response.json();
    } catch {
      // The packaged backend is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Packaged backend did not become ready.");
}

try {
  const health = await waitForHealth();
  const pairsResponse = await fetch("http://127.0.0.1:8000/api/v1/live/pairs");
  const accountResponse = await fetch("http://127.0.0.1:8000/api/v1/live/account");
  if (!pairsResponse.ok || !accountResponse.ok) {
    throw new Error("A packaged read-only endpoint returned an error.");
  }
  const pairs = await pairsResponse.json();
  const account = await accountResponse.json();
  const tradablePairs = pairs.pairs.filter((pair) => pair.tradable).length;
  const assets = account.balances
    .filter((balance) => balance.total !== 0)
    .map((balance) => balance.display_symbol)
    .sort();
  console.log(`packaged_health=${health.status}`);
  console.log(`packaged_tradable_eur_pairs=${tradablePairs}`);
  console.log(`packaged_nonzero_asset_symbols=${assets.join(",")}`);
  console.log(`packaged_account_status=${account.connection_status}`);
} finally {
  backend.kill();
}
