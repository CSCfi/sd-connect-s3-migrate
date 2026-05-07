import { app, BrowserWindow, ipcMain, powerSaveBlocker } from "electron";
import path from "node:path";
import started from "electron-squirrel-startup";
import fs from "fs/promises";

/**
 * @typedef {import { MigrationState } from "scripts/types.js";}
 */

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (started) {
  app.quit();
}

// Sourced from: https://pratikpc.medium.com/bypassing-cors-with-electron-ab7eaf331605
function UpsertKeyValue(obj, keyToChange, value) {
  const keyToChangeLower = keyToChange.toLowerCase();
  for (const key of Object.keys(obj)) {
    if (key.toLowerCase() === keyToChangeLower) {
      // Reassign old key
      obj[key] = value;
      // Done
      return;
    }
  }
  // Insert at end instead
  obj[keyToChange] = value;
}

// Resumable migration process logic
const STATE_FILE_PATH = path.join(app.getPath("documents"), "SD-Connect-S3-Migrate", "migration-state.json");

/**
 * Handle the migration state save event
 * @param {*} _event - placefolder for the event
 * @param {MigrationState} state - the current state of the migration
 */
async function saveMigrationStateHandler(_event, state) {
  if (!app.isPackaged) {
    console.log(`Main thread saving following state: ${state}`);
  }

  try {
    await fs.mkdir(path.dirname(STATE_FILE_PATH), { recursive: true });
    await fs.writeFile(STATE_FILE_PATH, JSON.stringify(state, null, 2), "utf-8");
  } catch (e) {
    console.log("Failed to save the migration state.");
    console.log(e);
  }
}

/**
 * Handle the migration state load event
 * @returns {MigrationState}
 */
async function loadMigrationStateHandler() {
  try {
    const data = await fs.readFile(STATE_FILE_PATH, "utf-8");
    const state = JSON.parse(data);

    if (!app.isPackaged) {
      console.log(`Main thread loaded following state: ${state}`);
    }

    return state;
  } catch {
    return null; // first run or file deleted by user
  }
}

/**
 * Handle the migration state clear event
 */
async function clearMigrationStateHandler() {
  try {
    const t = new Date();
    // Rename the existing state if it exists when the user cancels the resume.
    // We'll keep the old versions with a date stamp attached.
    await fs.rename(STATE_FILE_PATH, `${STATE_FILE_PATH.replaceAll(".json", "")}-canceled-${t.toISOString()}.json`);
  } catch (e) {
    console.log("Failed to clear migration state.");
    console.log(e);
    return;
  }
}

/**
 * Handle the migration state finish event
 */
async function finishMigrationStateHandler() {
  try {
    // Rename the current state once the migration is finished.
    // We'll keep the old versions with a date stamp attached.
    const t = new Date();
    await fs.rename(STATE_FILE_PATH, `${STATE_FILE_PATH.replaceAll(".json", "")}-finished-${t.toISOString()}.json`);
  } catch (e) {
    console.log("Failed to rename finished migration state.");
    console.log(e);
    return;
  }
}

ipcMain.handle("save-migration-state", saveMigrationStateHandler);
ipcMain.handle("load-migration-state", loadMigrationStateHandler);
ipcMain.handle("clear-migration-state", clearMigrationStateHandler);
ipcMain.handle("finish-migration-state", finishMigrationStateHandler);

// Expose development mode on the rendered process
const devMode = !app.isPackaged;
ipcMain.handle("get-devmode", () => {
  return devMode;
});

const createWindow = () => {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: true,
      enableRemoteModule: true,
      nodeIntegrationInWorker: true,
      nodeIntegrationInSubFrames: true,
      webSecurity: false,
    },
  });

  mainWindow.webContents.session.webRequest.onBeforeSendHeaders((details, callback) => {
    const { requestHeaders } = details;
    UpsertKeyValue(requestHeaders, "Origin", "*");
    UpsertKeyValue(requestHeaders, "Sec-Fetch-Mode", "no-cors");
    UpsertKeyValue(requestHeaders, "Sec-Fetch-Site", "none");
    UpsertKeyValue(requestHeaders, "Sec-Fetch-Dest", "document");
    callback({
      requestHeaders,
    });
  });

  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    const { responseHeaders } = details;
    UpsertKeyValue(responseHeaders, "Access-Control-Allow-Origin", ["*"]);
    UpsertKeyValue(responseHeaders, "Access-Control-Allow-Headers", ["*"]);
    UpsertKeyValue(responseHeaders, "Access-Control-Expose-Headers", ["*"]);
    // Prevent executing scripts that are not sourced from the local environment
    UpsertKeyValue(responseHeaders, "Content-Security-Policy", ["script-src 'self'"]);
    callback({
      responseHeaders,
    });
  });

  // and load the index.html of the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`));
  }

  // Open the DevTools.
  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools();
  }
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  createWindow();

  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and import them here.

// Prevent app from suspending on cue from renderer channel
let blockerId = null;

ipcMain.on("power-save-block:start", () => {
  if (blockerId === null) {
    blockerId = powerSaveBlocker.start("prevent-app-suspension");
  }
});

ipcMain.on("power-save-block:stop", () => {
  if (blockerId !== null) {
    powerSaveBlocker.stop(blockerId);
    blockerId = null;
  }
});
