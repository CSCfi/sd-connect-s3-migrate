// See the Electron documentation for details on how to use preload scripts:
// https://www.electronjs.org/docs/latest/tutorial/process-model#preload-scripts

/**
 * @typedef {import { MigrationState } from "scripts/types.js";}
 */

import { contextBridge, ipcRenderer } from "electron";

/**
 * Save the migration state via IPC in the main node thread.
 * @param {MigrationState} state - the migration state to save
 * @returns {Promise<undefined>}
 */
async function saveMigrationStateCallback(state) {
  return await ipcRenderer.invoke("save-migration-state", state);
}

/**
 * Load the migration state via IPC in the main node thread.
 * @returns {Promise<(MigrationState | null)>} - the loaded migration state
 */
async function loadMigrationStateCallback() {
  return await ipcRenderer.invoke("load-migration-state");
}

/**
 * Clear migration state via IPC in the main node thread.
 * @returns {Promise<undefined>}
 */
async function clearMigrationStateCallback() {
  return await ipcRenderer.invoke("clear-migration-state");
}

/**
 * Clear migration state via IPC in the main node thread.
 * @returns {Promise<undefined>}
 */
async function finishMigrationStateCallback() {
  return await ipcRenderer.invoke("finish-migration-state");
}

contextBridge.exposeInMainWorld("appEnv", {
  devMode: () => ipcRenderer.invoke("get-devmode"),
});

contextBridge.exposeInMainWorld("stateAPI", {
  saveState: saveMigrationStateCallback,
  loadState: loadMigrationStateCallback,
  clearState: clearMigrationStateCallback,
  finishState: finishMigrationStateCallback,
});

contextBridge.exposeInMainWorld("powerSaveBlocker", {
  start: () => ipcRenderer.send("power-save-block:start"),
  stop: () => ipcRenderer.send("power-save-block:stop"),
});
