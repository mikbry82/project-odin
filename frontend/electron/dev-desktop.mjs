import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const electronExecutable = require("electron");
const npmExecutable = process.platform === "win32" ? "npm.cmd" : "npm";
let viteProcess = null;

async function frontendIsReady() {
  try {
    const response = await fetch("http://127.0.0.1:5173", {
      signal: AbortSignal.timeout(800),
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForFrontend() {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (await frontendIsReady()) return true;
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  return false;
}

if (!(await frontendIsReady())) {
  viteProcess = spawn(npmExecutable, ["run", "dev"], {
    stdio: "inherit",
    windowsHide: true,
  });
}

if (!(await waitForFrontend())) {
  console.error("Frontend-servern kunde inte starta på http://127.0.0.1:5173.");
  viteProcess?.kill();
  process.exit(1);
}

const electronProcess = spawn(electronExecutable, ["."], {
  stdio: "inherit",
  env: {
    ...process.env,
    ELECTRON_RUN_AS_NODE: undefined,
    ODIN_ELECTRON_DEV: "1",
  },
  windowsHide: true,
});

electronProcess.once("exit", (code) => {
  viteProcess?.kill();
  process.exit(code ?? 0);
});
