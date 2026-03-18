// Convenience functions for accessing openstack

const auth_endpoint = "https://pouta-test.csc.fi:5001";
let object_storage_endpoint = "";
let userId = "";

// Login using username and password
export async function loginWithUserpass(username, password) {
  let unscoped = "";

  const resp = await fetch(new URL("/v3/auth/tokens", auth_endpoint), {
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
    console.log("Login not successful");
    return unscoped;
  }

  // Cache the user id
  const unscopedResponse = await resp.json();
  console.log(unscopedResponse);
  userId = unscopedResponse?.token?.user?.id;
  console.log(`User id: ${userId}`);

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
  const resp = await fetch(new URL("/v3/OS-FEDERATION/projects", auth_endpoint), {
    method: "GET",
    headers: {
      "X-Auth-Token": token,
    },
  });

  if (resp.status != 200) {
    console.log("Could not retrieve projects");
  }

  const resp_projects = await resp.json();
  const projects = resp_projects.projects.filter((project) => project.enabled);

  return projects;
}

// Retrieve a scoped project token
export async function getScopedToken(token, project) {
  let scoped = "";

  const resp = await fetch(new URL("/v3/auth/tokens", auth_endpoint), {
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
    console.log("Could not retrieve a scoped token.");
    return scoped;
  }

  scoped = resp.headers.get("X-Subject-Token");

  // Cache the endpoint for object storage
  let login_meta = await resp.json();
  object_storage_endpoint = login_meta.token.catalog
    .filter((service) => service.type === "object-store")[0]
    .endpoints.filter((endpoint) => endpoint.interface === "public")[0].url;

  console.log(object_storage_endpoint);

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
    console.log("No user id is defined, cannot retrieve ec2 credentials.");
    return;
  }

  let ec2;

  try {
    const resp = await fetch(new URL(`/v3/users/${userId}/credentials/OS-EC2`, auth_endpoint), {
      headers: {
        "X-Auth-Token": token,
      },
    });

    const creds = await resp.json();
    ec2 = creds?.credentials?.find((credential) => credential?.type === "ec2" && credential?.tenant_id === projectId);
    if (!ec2) {
      throw new Error("No credentials listed");
    }
  } catch (e) {
    console.log(e);
    console.log("Failed to retrieve EC2 credentials.");
    console.log("Trying to generate EC2 credentials.");

    const resp = await fetch(new URL(`/v3/users/${userId}/credentials/OS-EC2`, auth_endpoint), {
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

  console.log(ec2);

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
      });

      bucket_page = await resp.json();
      if (bucket_page.length > 0) buckets = [...buckets, ...bucket_page];
      marker = buckets[buckets.length - 1]?.name ?? "";
    } catch (e) {
      console.log(e);
      break;
    }
  } while (bucket_page?.length > 0);

  console.log(buckets);

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
    });

    let readAcl = resp.headers.get("X-Container-Read");
    let writeAcl = resp.headers.get("X-Container-Write");

    console.log(readAcl);
    console.log(writeAcl);

    // Parse the ACLs, we assume there will be no role based ACL entries as they're not
    // really supported for normal Allas users.
    if (readAcl) {
      ACLs.read = readAcl
        .replaceAll(" ", "") // get rid of spaces, that are allowed in Openstack spec
        .split(",") // split the listing to a list of share entries
        .filter((item) => !item.match(".r") && !item.match(".rlistings")) // filter out global shares if they exist
        .filter((item) => !item.match("*.*")) // filter out the authenticated global share if it exists
        .map((item) => item.split(":")[0]); // yank the projects from the ACL listing, we don't care about the trailing asterisk
    }
    if (writeAcl) {
      ACLs.write = writeAcl
        .replaceAll(" ", "") // get rid of spaces, that are allowed in Openstack spec
        .split(",") // split the listing to a list of share entries
        .filter((item) => !item.match("*.*")) // filter out the authenticated global share if it exists
        .map((item) => !item.split(":")[0]); // yank the projects from the ACL listing, we don't care about the trailing asterisk
    }
  } catch (e) {
    console.log("Failed to retrieve bucket ACLs.");
    console.log(e);
  }

  console.log(ACLs);
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
      });

      object_page = await resp.json();
      if (object_page.length > 0) objects = [...objects, ...object_page];
      marker = objects[objects.length - 1]?.name ?? "";
    } catch (e) {
      console.log(e);
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
    });

    // Currently we only support DLO manifests, not SLO, as SD Connect tools
    // don't use SLO anywhere
    manifest = resp.headers.get("X-Object-Manifest");
    console.log(manifest);
  } catch (e) {
    console.log(e);
  }

  return manifest;
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
    });

    objectMeta.size = Number(resp.headers.get("Content-Length"));
    objectMeta.last_modified = resp.headers.get("Last-Modified");
  } catch (e) {
    console.log(e);
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
    console.log(e);
  }

  console.log(object);

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
    });

    // retrieve the etag from the response
    etag = resp.headers.get("ETag");
  } catch (e) {
    console.log(e);
  }

  return etag;
}
