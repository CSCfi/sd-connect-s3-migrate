// See the Electron documentation for details on how to use preload scripts:
// https://www.electronjs.org/docs/latest/tutorial/process-model#preload-scripts

/**
 * @typedef {import { MigrationState } from "scripts/types.js";}
 */

import { contextBridge, ipcRenderer } from "electron";

/**
 * Save the migration state via IPC in the main node thread.
 * @param {MigrationState} state
 */
function saveMigrationStateCallback(state) {
  ipcRenderer.invoke("save-migration-state", state);
}

/**
 * Load the migration state via IPC in the main node thread.
 * @returns {MigrationState}
 */
function loadMigrationStateCallback() {
  return ipcRenderer.invoke("load-migration-state");
}

/**
 * Clear migration state via IPC in the main node thread.
 * @returns
 */
function clearMigrationStateCallback() {
  return ipcRenderer.invoke("clear-migration-state");
}

contextBridge.exposeInMainWorld("appEnv", {
    devMode: () => ipcRenderer.invoke("get-devmode"),
});

contextBridge.exposeInMainWorld("stateAPI", {
  saveState: saveMigrationStateCallback,
  loadState: loadMigrationStateCallback,
  clearState: clearMigrationStateCallback,
});
