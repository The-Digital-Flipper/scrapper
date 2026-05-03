const { app, BrowserWindow, shell, Menu } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const path = require('path');

const APP_ROOT = app.isPackaged
  ? path.join(process.resourcesPath, 'appdata')
  : path.resolve(__dirname, '..');
const BACKEND_ROOT = app.isPackaged
  ? path.join(process.resourcesPath, 'backend-dist')
  : path.join(path.resolve(__dirname, '..'), 'backend-dist');
const BACKEND_BINARY = process.platform === 'win32'
  ? 'advanced-scraper-backend.exe'
  : 'advanced-scraper-backend';
const PORT = process.env.ADVANCED_SCRAPER_PORT || '8801';
const DASHBOARD_URL = `http://127.0.0.1:${PORT}`;
let serverProcess = null;
let windowRef = null;

function isDashboardReady() {
  return new Promise((resolve) => {
    const req = http.get(DASHBOARD_URL, (res) => {
      res.resume();
      resolve(res.statusCode && res.statusCode < 500);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(500, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForDashboard(maxAttempts = 40) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (await isDashboardReady()) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function getBundledBackendPath() {
  const candidates = [
    path.join(BACKEND_ROOT, BACKEND_BINARY),
    path.join(BACKEND_ROOT, 'bin', BACKEND_BINARY),
    path.join(APP_ROOT, BACKEND_BINARY)
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function startDashboard() {
  if (serverProcess) {
    return;
  }
  const bundledBackend = getBundledBackendPath();
  const env = { ...process.env, ADVANCED_SCRAPER_PORT: PORT };
  if (bundledBackend) {
    serverProcess = spawn(
      bundledBackend,
      [],
      {
        cwd: APP_ROOT,
        env,
        stdio: 'ignore',
        detached: process.platform !== 'win32'
      }
    );
  } else if (!app.isPackaged) {
    const python = process.platform === 'win32' ? 'python' : 'python3';
    serverProcess = spawn(
      python,
      ['-m', 'advanced_scraper.product'],
      {
        cwd: APP_ROOT,
        env,
        stdio: 'ignore',
        detached: process.platform !== 'win32'
      }
    );
  } else {
    throw new Error('Bundled backend executable not found. Rebuild the desktop package.');
  }
  if (serverProcess.unref) {
    serverProcess.unref();
  }
}

async function createWindow() {
  startDashboard();
  await waitForDashboard();

  const win = new BrowserWindow({
    width: 1500,
    height: 980,
    backgroundColor: '#050805',
    title: 'Advanced Scraper',
    show: false,
    icon: path.join(APP_ROOT, 'advanced-scraper-icon.svg'),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  win.once('ready-to-show', () => win.show());
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
  await win.loadURL(DASHBOARD_URL);
  windowRef = win;
  win.on('closed', () => {
    windowRef = null;
  });
}

function buildMenu() {
  const template = [
    {
      label: 'Advanced Scraper',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { type: 'separator' },
        { label: 'Open Dashboard', click: () => windowRef && windowRef.loadURL(DASHBOARD_URL) },
        { label: 'Open Preview', click: () => windowRef && windowRef.loadURL(`${DASHBOARD_URL}/preview`) },
        { label: 'Runs', click: () => windowRef && windowRef.loadURL(`${DASHBOARD_URL}/runs`) },
        { label: 'Archives', click: () => windowRef && windowRef.loadURL(`${DASHBOARD_URL}/archives`) },
        { type: 'separator' },
        { role: 'quit' }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.whenReady().then(async () => {
  buildMenu();
  await createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow().catch(() => {});
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (serverProcess && !serverProcess.killed) {
    try {
      serverProcess.kill();
    } catch (_) {
      // Best effort cleanup.
    }
  }
});
