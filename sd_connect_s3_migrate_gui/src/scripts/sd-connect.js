// Convenience functions for accessing SD Connect


import * as crypto from "crypto";

import { SD_CONNECT_API_URL } from "./config";


/**
 * A signature for an SD Connect API request
 * @typedef {Object} Signature
 * @property {string} signature - the signature of the request
 * @property {string} valid - the time of validity of the signature
 */

/**
 * A project ID pair
 * @typedef {Object} IDs
 * @property {string} id - the id of the project on keystone
 * @property {string} name - the name of the project on keystone
 */


/**
 * Sign an API request for use on the SD Connect API.
 * @param {string} apiKey - API key to be used when signing
 * @param {string} path - API path to be signed
 * @param {number} lifetime - lifetime in seconds describing how long the signature is valid
 * @returns {Signature} - the signature for the request
 */
export function sign_api_request(apiKey, path, lifetime = 3600) {
  // Convert the calculated lifetime to a string
  const validUntil = (Math.floor(Date.now() / 1000) + lifetime).toString;
  const toSign = `${validUntil}${path}`

  // Get the signature
  const key = Buffer.from(key);
  return {
    signature: crypto.createHmac("sha256", key).update(toSign).digest("hex"),
    valid: validUntil,
  };
}


/**
 * Retrieve the project public key from the SD Connect API.
 * @param {string} apiKey - the API key used when signing requests
 * @param {string} projectName - the name of the project used
 * @returns {Promise<string>} - the project's public key
 * @throws
 */
async function _getProjectPublicKey(apiKey, projectName) {
  // Sign the path
  const path = `/cryptic/${projectName}/keys`;
  const signature = sign_api_request(apiKey, path);

  // Prepare the URL
  let keyUrl = new URL(`${SD_CONNECT_API_URL}/runner${path}`);
  keyUrl.searchParams.append("signature", signature.signature);
  keyUrl.searchParams.append("valid", signature.valid);

  try {
    const keyResp = await fetch(keyUrl);
    const key = await keyResp.json();
    return key;
  } catch (e) {
    console.log("Failed to retrieve the project public key");
    console.log(e);
    throw e;
  }
}


/**
 * Whitelist the project's public key on the SD Connect API.
 * @param {string} apiKey - the API key used when signing requests
 * @param {string} projectName - the name of the project used
 * @throws
 */
export async function addProjectKeyToWhitelist(apiKey, projectName) {
  let projectKey;
  try {
    projectKey = await _getProjectPublicKey(apiKey, projectName);
  } catch (e) {
    console.log("Aborting header retrieval due to no available project public key.");
    throw new Error("Could not retrieve project public key for addition.");
  }

  // Sign the path
  const path = `/cryptic/${projectName}/whitelist`;
  const signature = sign_api_request(apiKey, path);
  
  // Prepare the URL
  let keyUrl = new URL(`${SD_CONNECT_API_URL}/runner${path}`);
  keyUrl.searchParams.append("signature", signature.signature);
  keyUrl.searchParams.append("valid", signature.valid);

  try {
    await fetch(keyUrl, {
      method: "PUT",
      body: projectKey,
    });
  } catch(e) {
    console.log("Failed to add the project public key to re-encryption whitelist.");
    console.log(e);
    throw new Error("Could not add project public key to whitelist.");
  }
}


/**
 * Remove the project's public key from the SD Connect API whitelist.
 * @param {string} apiKey - the API key used when signing requests
 * @param {string} projectName - the name of the project used
 * @throws
 */
export async function removeProjectKeyFromWhitelist(apiKey, projectName) {
  // Sign the path
  const path = `/cryptic/${projectName}/whitelist`;
  const signature = sign_api_request(apiKey, path);

  // Prepare the URL
  let keyUrl = new URL(`${SD_CONNECT_API_URL}/runner${path}`);
  keyUrl.searchParams.append("signature", signature.signature);
  keyUrl.searchParams.append("valid", signature.valid);

  try {
    await fetch(keyUrl, {
      method: "DELETE",
    });
  } catch (e) {
    console.log("Failed to delete the project public key from re-encryption whitelist.");
    console.log(e);
    throw new Error("Could not remove the project public key from the whitelist.");
  }
}


/**
 * Retrieve the project-key encrypted file header from SD Connect API.
 * @param {string} apiKey - the API key used when signing requests
 * @param {string} projectName - the name of the project used
 * @param {string} bucket - the bucket of the header
 * @param {string} key - the object key of the header
 * @returns {Promise<Uint8Array>}
 * @throws
 */
export async function getFileHeader(apiKey, projectName, bucket, key) {
  // Sign the path
  const path = `/header/${projectName}/${bucket}/${key}`;
  const signature = sign_api_request(apiKey, path);

  // Prepare the URL
  let keyUrl = new URL(`${SD_CONNECT_API_URL}/runner${path}`);
  keyUrl.searchParams.append("signature", signature.signature);
  keyUrl.searchParams.append("valid", signature.valid);

  try {
    const headerResp = await fetch(keyUrl);
    const header = await headerResp.bytes();
    if (header.length > 0) {
      return header;
    }
    throw new Error("Header was empty.");
  } catch (e) {
    console.log("Failed to retrieve a working header for the file.");
    console.log("The file may be added for v1.");
    console.log(e);
    throw new Error("No header for file.");
  }
}


/**
 * Put the project-key encrypted file header into SD Connect API.
 * @param {string} apiKey - the API key used when signing requests
 * @param {string} projectName - the name of the project used
 * @param {string} bucket - the bucket of the header
 * @param {string} key - the object key of the header
 * @param {Uint8Array} header - the object header to be added
 * @throws
 */
export async function putFileHeader(apiKey, projectName, bucket, key, header) {
  // Sign the path
  const path = `/header/${projectName}/${bucket}/${key}`;
  const signature = sign_api_request(apiKey, path);

  // Prepare the URL
  let keyUrl = new URL(`${SD_CONNECT_API_URL}/runner${path}`);
  keyUrl.searchParams.append("signature", signature.signature);
  keyUrl.searchParams.append("valid", signature.valid);

  try {
    const headerResp = await fetch(keyUrl, {
      method: "PUT",
      body: header,
    });
    if (headerResp.status != 204) {
      throw new Error("Failed to add a new header.");
    }
  } catch (e) {
    console.log("Failed to put header for the file.");
    console.log(e);
    throw new Error("Header addition failed.");
  }
}


/**
 * Get the sharing whitelist for a bucket.
 * @param {*} apiKey - the API key used when signing requests
 * @param {*} projectName - the name of the project used
 * @param {*} bucket - the bucket of the sharing whitelist
 * @returns {Promise<Array<string>>} - the sharing whitelist in the bucket
 */
export async function getSharingWhitelist(apiKey, projectName, bucket) {
  let whitelist = [];

  // Sign the path
  const path = `/cryptic/${projectName}/${bucket}`;
  const signature = sign_api_request(apiKey, path);

  // Prepare the URL
  let sharingWhitelistUrl = new URL(`${SD_CONNECT_API_URL}/runner${path}`);
  sharingWhitelistUrl.searchParams.append("signature", signature.signature);
  sharingWhitelistUrl.searchParams.append("valid", signature.valid);

  try {
    const whitelistResp = await fetch(sharingWhitelistUrl);
    whitelist = await whitelistResp.json();
  } catch(e) {
    console.log("Failed to retrieve bucket sharing whitelist");
    console.log(e);
    whitelist = [];
  }

  return whitelist;
}


/**
 * Check the project IDs.
 * @param {string} projectName - the project name to check
 * @returns {Promise<IDs>} - the IDs of the requested project
 */
export async function checkProjectIDs(projectName) {
  let idUrl = new URL(`${SD_CONNECT_API_URL}/sharing/ids/${projectName}`);

  let ids = {}
  try {
    const idResp = await fetch(idUrl);
    ids = await idResp.json();
  } catch (e) {
    console.log("Failed to retrieve the project id query");
    console.log(e)
    return {}
  }

  return ids;
}


/**
 * Add a formatted sharing whitelist to a bucket.
 * @param {string} apiKey - the API key used when signing requests
 * @param {string} projectName - the name of the project used
 * @param {string} bucket - the bucket of the new sharing whitelist
 * @param {Array<IDs>} whitelist - a list of projects to share to
 * @throws
 */
export async function putSharingWhitelist(apiKey, projectName, bucket, whitelist) {
  // Sign the path
  const path = `/cryptic/${projectName}/${bucket}`;
  const signature = sign_api_request(apiKey, path);

  // Prepare the URL
  let sharingWhitelistUrl = new URL(`${SD_CONNECT_API_URL}/runner${path}`);
  sharingWhitelistUrl.searchParams.append("signature", signature.signature);
  sharingWhitelistUrl.searchParams.append("valid", signature.valid);

  try {
    await fetch(sharingWhitelistUrl, {
      method: "PUT",
      body: JSON.stringify(whitelist),
    });
  } catch(e) {
    console.log("Failed to put bucket sharing whitelist.");
    console.log(e);
    throw new Error("Failed to add bucket sharing whitelist.");
  }
}
