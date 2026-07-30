import { app, BrowserWindow, protocol, session } from "electron";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8000;
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const STARTUP_TIMEOUT_MS = 30_000;
const isDevelopment = process.env.ODIN_ELECTRON_DEV === "1";
const electronDirectory = path.dirname(fileURLToPath(import.meta.url));

let backendProcess = null;
let mainWindow = null;
let backendStartedByElectron = false;
let allowQuit = false;

protocol.registerSchemesAsPrivileged([
  {
    scheme: "app",
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
    },
  },
]);

function contentType(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  return (
    {
      ".css": "text/css; charset=utf-8",
      ".html": "text/html; charset=utf-8",
      ".js": "text/javascript; charset=utf-8",
      ".json": "application/json; charset=utf-8",
      ".svg": "image/svg+xml",
      ".png": "image/png",
      ".ico": "image/x-icon",
    }[extension] ?? "application/octet-stream"
  );
}

async function registerApplicationProtocol() {
  const frontendRoot = path.join(process.resourcesPath, "frontend");
  protocol.handle("app", async (request) => {
    const requestUrl = new URL(request.url);
    const relativePath =
      decodeURIComponent(requestUrl.pathname).replace(/^\/+/, "") ||
      "index.html";
    const resolvedPath = path.resolve(frontendRoot, relativePath);
    if (!resolvedPath.startsWith(`${path.resolve(frontendRoot)}${path.sep}`)) {
      return new Response("Not found", { status: 404 });
    }
    try {
      const contents = await readFile(resolvedPath);
      return new Response(contents, {
        headers: { "content-type": contentType(resolvedPath) },
      });
    } catch {
      return new Response("Not found", { status: 404 });
    }
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 960,
    minHeight: 640,
    show: false,
    backgroundColor: "#070b14",
    title: "Project Odin",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  mainWindow.webContents.on("will-attach-webview", (event) =>
    event.preventDefault(),
  );
  mainWindow.webContents.on("will-navigate", (event, targetUrl) => {
    try {
      const parsedUrl = new URL(targetUrl);
      const isAllowed = isDevelopment
        ? parsedUrl.origin === "http://127.0.0.1:5173"
        : parsedUrl.protocol === "app:" && parsedUrl.hostname === "odin";
      if (!isAllowed) event.preventDefault();
    } catch {
      event.preventDefault();
    }
  });
  mainWindow.once("ready-to-show", () => mainWindow?.show());
}

async function showStartup(message, detail = "") {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const startupFile = path.join(electronDirectory, "startup.html");
  await mainWindow.loadFile(startupFile, {
    query: { message, detail },
  });
}

async function backendIsHealthy() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 900);
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      signal: controller.signal,
    });
    const payload = await response.json();
    return response.ok && payload.status === "ok" && payload.database === "ok";
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

async function portIsAvailable() {
  return new Promise((resolve) => {
    const server = createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => server.close(() => resolve(true)));
    server.listen(BACKEND_PORT, BACKEND_HOST);
  });
}

function desktopEnvironment() {
  const databasePath = path
    .join(app.getPath("userData"), "project-odin.db")
    .replaceAll("\\", "/");
  return {
    ...process.env,
    APP_ENV: "desktop",
    APP_DEBUG: "false",
    DATABASE_URL: `sqlite+aiosqlite:///${databasePath}`,
    ODIN_LOG_FILE: path.join(app.getPath("userData"), "odin-backend.log"),
    DESKTOP_HOST: BACKEND_HOST,
    DESKTOP_PORT: String(BACKEND_PORT),
    CORS_ORIGINS: JSON.stringify(["app://odin", "http://127.0.0.1:5173"]),
  };
}

function startBackend() {
  const command = isDevelopment
    ? process.env.ODIN_PYTHON || "python"
    : path.join(process.resourcesPath, "backend", "project-odin-backend.exe");
  const args = isDevelopment ? ["-m", "app.desktop"] : [];
  const cwd = isDevelopment
    ? path.resolve(electronDirectory, "..", "..", "backend")
    : path.dirname(command);

  backendProcess = spawn(command, args, {
    cwd,
    env: desktopEnvironment(),
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
  });
  backendStartedByElectron = true;
  backendProcess.stdout?.resume();
  backendProcess.stderr?.resume();

  backendProcess.once("error", () => {
    void showStartup(
      "Odin kunde inte starta den lokala tjänsten.",
      "Kontrollera installationen och starta om programmet.",
    );
  });
  backendProcess.once("exit", (code) => {
    backendProcess = null;
    if (!allowQuit) {
      if (code === 2) {
        void showStartup(
          "Odins lokala konfiguration är ogiltig.",
          "Kontrollera miljöinställningarna utan att dela hemliga värden.",
        );
      } else if (code === 3) {
        void showStartup(
          "Port 8000 används redan.",
          "Stäng den andra processen och starta sedan om Project Odin.",
        );
      } else {
        void showStartup(
          "Odins lokala tjänst avslutades oväntat.",
          "Starta om programmet. Om problemet kvarstår, kontrollera konfigurationen.",
        );
      }
    }
  });
}

async function waitForBackend() {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await backendIsHealthy()) return true;
    if (backendStartedByElectron && !backendProcess) return false;
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  return false;
}

async function startApplication() {
  createWindow();
  await showStartup(
    "Project Odin startar…",
    "Förbereder den lokala tjänsten och dina data.",
  );

  if (!(await backendIsHealthy())) {
    if (!(await portIsAvailable())) {
      await showStartup(
        "Port 8000 används redan.",
        "Stäng den andra processen och starta sedan om Project Odin.",
      );
      return;
    }
    startBackend();
  }

  if (!(await waitForBackend())) {
    await showStartup(
      "Odin kunde inte starta inom 30 sekunder.",
      "Kontrollera den lokala konfigurationen och starta om programmet.",
    );
    return;
  }

  if (isDevelopment) {
    await mainWindow.loadURL("http://127.0.0.1:5173");
  } else {
    await mainWindow.loadURL("app://odin/index.html");
  }
}

async function stopBackend() {
  if (!backendProcess || !backendStartedByElectron) return;
  const processToStop = backendProcess;
  await new Promise((resolve) => {
    const forceStop = setTimeout(() => {
      processToStop.kill();
      resolve();
    }, 3_000);
    processToStop.once("exit", () => {
      clearTimeout(forceStop);
      resolve();
    });
    processToStop.stdin?.write("shutdown\n");
    processToStop.stdin?.end();
  });
}

const hasSingleInstanceLock = app.requestSingleInstanceLock();
if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.on("before-quit", (event) => {
    if (allowQuit || !backendProcess) return;
    event.preventDefault();
    allowQuit = true;
    void stopBackend().finally(() => app.quit());
  });

  app.whenReady().then(async () => {
    session.defaultSession.setPermissionRequestHandler(
      (_webContents, _permission, callback) => callback(false),
    );
    if (!isDevelopment) await registerApplicationProtocol();
    await startApplication();
  });

  app.on("window-all-closed", () => app.quit());
}
