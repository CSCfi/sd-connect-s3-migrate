// Convenience functions for accessing openstack

import { getOpenstackAuthEndpoint } from "./config";
import { devConsole } from "../renderer";

let object_storage_endpoint = "";
let userId = "";

// Login using username and password
export async function loginWithUserpass(username, password) {
  let unscoped = "";

  const resp = await fetch(new URL("/v3/auth/tokens", await getOpenstackAuthEndpoint()), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      auth: {
        identity: {
          methods: ["password"],
          password: {
            user: {
              name: username,
              domain: {
                name: "Default",
              },
              password: password,
            },
          },
        },
        scope: "unscoped",
      },
    }),
  });

  if (resp.status >= 400) {
    console.error(`Login not successful. Response status ${resp.status}.`);
    return unscoped;
  }

  // Cache the user id
  const unscopedResponse = await resp.json();
  userId = unscopedResponse?.token?.user?.id;
  console.log(`Logged-in user id: ${userId}`);

  unscoped = resp.headers.get("X-Subject-Token");

  return unscoped;
}

/**
 * Retrieve the S3 endpoint based on the object storage endpoint
 */
export function getS3endpoint() {
  return object_storage_endpoint.replaceAll("/swift/v1", "");
}

// Discover available projects from an unscoped token
export async function discoverTokenProjects(token) {
  const resp = await fetch(new URL("/v3/OS-FEDERATION/projects", await getOpenstackAuthEndpoint()), {
    method: "GET",
    headers: {
      "X-Auth-Token": token,
    },
  });

  if (resp.status != 200) {
    console.error(`Could not retrieve projects. Response status ${resp.status}`);
  }

  const resp_projects = await resp.json();
  const projects = resp_projects.projects.filter((project) => project.enabled);

  return projects;
}

// Retrieve a scoped project token
export async function getScopedToken(token, project) {
  let scoped = "";

  const resp = await fetch(new URL("/v3/auth/tokens", await getOpenstackAuthEndpoint()), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      auth: {
        identity: {
          methods: ["token"],
          token: {
            id: token,
          },
        },
        scope: {
          project: {
            id: project,
          },
        },
      },
    }),
  });

  if (resp.status != 200 && resp.status != 201) {
    console.error(`Could not retrieve a scoped token. Response status ${resp.status}.`);
    return scoped;
  }

  scoped = resp.headers.get("X-Subject-Token");

  // Cache the endpoint for object storage
  let login_meta = await resp.json();
  object_storage_endpoint = login_meta.token.catalog
    .filter((service) => service.type === "object-store")[0]
    .endpoints.filter((endpoint) => endpoint.interface === "public")[0].url;

  console.log("Set object storage endpoint:", object_storage_endpoint);

  return scoped;
}

/**
 * Retrieve ec2 credentials using the scoped project token
 * @param {string} token - a scoped token for the project in use
 * @param {string} projectId - the used project's ID
 * @returns {Promise<Object>} - the ec2 credentials
 */
export async function getEC2Credentials(token, projectId) {
  if (!userId) {
    console.error("No user id is defined, cannot retrieve EC2 credentials.");
    return;
  }

  let ec2;

  try {
    const resp = await fetch(new URL(`/v3/users/${userId}/credentials/OS-EC2`, await getOpenstackAuthEndpoint()), {
      headers: {
        "X-Auth-Token": token,
      },
    });

    const creds = await resp.json();
    ec2 = creds?.credentials?.find((credential) => credential?.type === "ec2" && credential?.tenant_id === projectId);
    if (!ec2) {
      throw new Error("Failed to retrieve EC2 credentials.");
    }
  } catch (e) {
    console.warn(e);
    console.warn("Trying to generate EC2 credentials.");

    const resp = await fetch(new URL(`/v3/users/${userId}/credentials/OS-EC2`, await getOpenstackAuthEndpoint()), {
      method: "POST",
      headers: {
        "X-Auth-Token": token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tenant_id: projectId,
      }),
    });

    const creds = await resp.json();
    ec2 = creds?.credential;
  }

  devConsole.log("EC2", ec2);
  console.log("Retrieved EC2 credentials");

  return ec2;
}

/**
 * Fetch a list of buckets from the Openstack Swift API
 * @param {string} token
 * @returns {Promise<Array>}
 */
export async function getBuckets(token) {
  let buckets = [];
  let marker = "";
  let bucket_page;

  do {
    try {
      const bucketURL = new URL("", object_storage_endpoint);
      // Use 100 as the bucket page limit
      bucketURL.searchParams.append("limit", 100);
      bucketURL.searchParams.append("format", "json");
      // Use the marker for paging the listings
      if (marker) {
        bucketURL.searchParams.append("marker", marker);
      }
      const resp = await fetch(bucketURL, {
        headers: {
          "X-Auth-Token": token,
        },
        cache: "no-cache",
      });

      bucket_page = await resp.json();
      if (bucket_page.length > 0) buckets = [...buckets, ...bucket_page];
      marker = buckets[buckets.length - 1]?.name ?? "";
    } catch (e) {
      console.error("Error retrieving buckets via Swift API:");
      console.error(e);
      break;
    }
  } while (bucket_page?.length > 0);

  devConsole.log("Buckets", buckets);
  console.log(`Retrieved ${buckets.length} buckets`);

  return buckets;
}

/**
 * Fetch the filtered bucket ACL header contents
 * @param {string} token
 * @param {string} bucket
 * @returns {Promise<Object>}
 */
export async function getBucketACLs(token, bucket) {
  let ACLs = {};

  try {
    const bucketURL = new URL(`${object_storage_endpoint}/${bucket}`);
    const resp = await fetch(bucketURL, {
      method: "HEAD",
      headers: {
        "X-Auth-Token": token,
      },
      cache: "no-cache",
    });

    let readAcl = resp.headers.get("X-Container-Read");
    let writeAcl = resp.headers.get("X-Container-Write");

    // Parse the ACLs, we assume there will be no role based ACL entries as they're not
    // really supported for normal Allas users.
    if (readAcl) {
      ACLs.read = readAcl
        .replaceAll(" ", "") // get rid of spaces, that are allowed in Openstack spec
        .split(",") // split the listing to a list of share entries
        .filter((item) => !item.match(/\.r/g) || !item.match(/\.rlistings/g)) // filter out global shares if they exist
        .filter((item) => !item.match(/\*\.\*/)) // filter out the authenticated global share if it exists
        .map((item) => item.split(":")[0]); // yank the projects from the ACL listing, we don't care about the trailing asterisk
    }
    if (writeAcl) {
      ACLs.write = writeAcl
        .replaceAll(" ", "") // get rid of spaces, that are allowed in Openstack spec
        .split(",") // split the listing to a list of share entries
        .filter((item) => !item.match(/\*\.\*/)) // filter out the authenticated global share if it exists
        .map((item) => item.split(":")[0]); // yank the projects from the ACL listing, we don't care about the trailing asterisk
    }
  } catch (e) {
    console.error("Failed to retrieve bucket ACLs:");
    console.error(e);
  }

  if (Object.keys(ACLs).length) {
    console.log(`Retrieved bucket ${bucket} ACLs:`);
    console.log(ACLs);
  } else {
    console.log(`No ACL entries exist for bucket ${bucket}`);
  }

  return ACLs;
}

/**
 * Fetch a list of objects within a bucket
 * @param {string} token
 * @param {string} bucket
 * @returns {Promise<Array>}
 */
export async function getObjects(token, bucket, prefix = "") {
  let objects = [];
  let marker = "";
  let object_page;

  do {
    try {
      let objectURL = new URL(`${object_storage_endpoint}/${bucket}`);
      // Use 1000 as the object page limit
      objectURL.searchParams.append("limit", 1000);
      objectURL.searchParams.append("format", "json");
      // Use the marker for paging the listings
      if (marker) {
        objectURL.searchParams.append("marker", marker);
      }
      // If there's a prefix, provide a listing filtered by a prefix
      if (prefix) {
        objectURL.searchParams.append("path", prefix);
        // Use / as the default delimiter for directory traversal
        // objectURL.searchParams.append("delimiter", "/");
      }
      let resp = await fetch(objectURL, {
        headers: {
          "X-Auth-Token": token,
        },
        cache: "no-cache",
      });

      object_page = await resp.json();
      if (object_page.length > 0) objects = [...objects, ...object_page];
      marker = objects[objects.length - 1]?.name ?? "";
    } catch (e) {
      console.error(`Error retrieving objects for ${bucket} via Swift API:`);
      console.error(e);
      break;
    }
  } while (object_page?.length > 0);

  return objects;
}

/**
 * Retrieve the DLO manifest prefix for a Swift large object
 * @param {string} token - a scoped openstack auth token
 * @param {string} bucket - the bucket the object is in
 * @param {string} key - the name of the object
 * @returns {Promise<string>} - the DLO manifest prefix
 */
export async function checkObjectManifest(token, bucket, key) {
  let manifest = "";
  try {
    const objectURL = new URL(`${object_storage_endpoint}/${bucket}/${key}`);
    const resp = await fetch(objectURL, {
      method: "HEAD",
      headers: {
        "X-Auth-Token": token,
      },
      cache: "no-cache",
    });

    // Currently we only support DLO manifests, not SLO, as SD Connect tools
    // don't use SLO anywhere
    manifest = resp.headers.get("X-Object-Manifest");
    console.log(`Object ${key} manifest: ${manifest}`);
  } catch (e) {
    console.error(`Error retrieving object ${key} manifest:`);
    console.error(e);
  }

  return manifest;
}

/**
 * Put the manifest object for a DLO
 * @param {string} token - a scoped openstack auth token
 * @param {string} bucket - the bucket the object is in
 * @param {string} key - the name of the object
 * @param {string} manifest - DLO manifest
 */
export async function putManifestObject(token, bucket, key, manifest) {
  try {
    const objectURL = new URL(`${object_storage_endpoint}/${bucket}/${key}`);
    const resp = await fetch(objectURL, {
      method: "PUT",
      headers: {
        "X-Auth-Token": token,
        "X-Object-Manifest": manifest,
        "Content-Length": 0,
      },
    });
    if (!resp.ok) {
      const error = new Error("HTTP error");
      error.status = resp.status;
      throw error;
    }
    console.log(`Put manifest object for ${key} in ${bucket}`);
  } catch (e) {
    console.error(`Failed to put manifest object for ${key} in ${bucket}:`);
    console.error(e);
  }
}

/**
 * Retrieve the required object metadata headers
 * @param {string} token - a scoped openstack auth token
 * @param {string} bucket - the bucket the object is in
 * @param {string} key - the name of the object
 * @returns {Promise<Object>} - the relevant object metadata
 */
export async function getObjectMeta(token, bucket, key) {
  let objectMeta = {
    size: 0,
    last_modified: "",
  };
  try {
    const objectURL = new URL(`${object_storage_endpoint}/${bucket}/${key}`);
    const resp = await fetch(objectURL, {
      method: "HEAD",
      headers: {
        "X-Auth-Token": token,
      },
      cache: "no-cache",
    });

    objectMeta.size = Number(resp.headers.get("Content-Length"));
    objectMeta.last_modified = resp.headers.get("Last-Modified");
  } catch (e) {
    console.error(`Error retrieving object ${key} metadata via Swift API:`);
    console.error(e);
  }

  return objectMeta;
}

/**
 * Retrieve a byte range of the object
 * @param {string} token - a scoped openstack auth token
 * @param {string} bucket - the bucket the object is in
 * @param {string} key - the name of the object
 * @param {number} start - first byte of the range
 * @param {number} end - last byte of the range (inclusive range)
 * @returns {Promise<Uint8Array>} - the object contents
 */
export async function getObject(token, bucket, key, start = 0, end = 200 * 1024 * 1024 - 1) {
  console.log(`Getting object ${key} bytes ${start}-${end}`);

  let object = new Uint8Array([]);

  try {
    let objectURL = new URL(`${object_storage_endpoint}/${bucket}/${key}`);
    const resp = await fetch(objectURL, {
      method: "GET",
      headers: {
        "X-Auth-Token": token,
        Range: `bytes=${start}-${end}`,
      },
      cache: "no-cache",
    });

    object = await resp.bytes();
  } catch (e) {
    console.error(`Error retrieving object ${key} via Swift API:`);
    console.error(e);
  }

  console.log(`Retrieved object ${key}`);
  devConsole.log(object);

  return object;
}

/**
 *
 * @param {string} token - a scoped openstack auth token
 * @param {string} bucket - the bucket the object is in
 * @param {string} key - the name of the object
 * @returns {Promise<string>} - The object metadata headers
 */
export async function getObjectEtag(token, bucket, key) {
  let etag = "";

  try {
    const objectURL = new URL(`${object_storage_endpoint}/${bucket}/${key}`);
    const resp = await fetch(objectURL, {
      method: "HEAD",
      headers: {
        "X-Auth-Token": token,
      },
      cache: "no-cache",
    });

    // retrieve the etag from the response
    etag = resp.headers.get("ETag");
  } catch (e) {
    console.error(`Error retrieving object ${key} etag via Swift API:`);
    console.error(e);
  }

  return etag;
}

/**
 * Delete a bucket
 * @param {string} token - a scoped OpenStack auth token
 * @param {string} bucket - the name of the bucket
 * @returns {Promise<boolean>} - true if deleted successfully
 */
export async function deleteBucket(token, bucket) {
  console.log(`Deleting bucket ${bucket}`);

  try {
    const bucketURL = new URL(`${object_storage_endpoint}/${bucket}`);

    const resp = await fetch(bucketURL, {
      method: "DELETE",
      headers: {
        "X-Auth-Token": token,
      },
    });

    if (!resp.ok) {
      throw new Error(`Failed to delete bucket ${bucket}: ${resp.status} ${resp.statusText}`);
    }
    return true;
  } catch (e) {
    console.error(e);
    return false;
  }
}

/**
 * Delete an object
 * @param {string} token - a scoped OpenStack auth token
 * @param {string} bucket - the bucket the object is in
 * @param {string} key - the name of the object
 * @returns {Promise<boolean>} - true if deleted successfully
 */
export async function deleteObject(token, bucket, key) {
  console.log(`Deleting object ${key}`);

  try {
    const objectURL = new URL(`${object_storage_endpoint}/${bucket}/${key}`);

    const resp = await fetch(objectURL, {
      method: "DELETE",
      headers: {
        "X-Auth-Token": token,
      },
    });

    if (!resp.ok) {
      throw new Error(`Failed to delete object ${key}: ${resp.status} ${resp.statusText}`);
    }

    return true;
  } catch (e) {
    console.error(e);
    return false;
  }
}
