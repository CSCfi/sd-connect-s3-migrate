// Convenience functions for accessing openstack

const auth_endpoint = "https://pouta-test.csc.fi:5001";
let object_storage_endpoint = "";


// Login using username and password
export async function loginWithUserpass(username, password) {
  let unscoped = "";

  const resp = await fetch(
    new URL("/v3/auth/tokens", auth_endpoint),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        auth: {
          identity: {
            methods: [
              "password"
            ],
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
    },
  );

  if (resp.status >= 400) {
    console.log("Login not successful");
    return unscoped;
  }

  unscoped = resp.headers.get("X-Subject-Token");

  return unscoped;
}


// Discover available projects from an unscoped token
export async function discoverTokenProjects(token) {
  let projects = [];

  const resp = await fetch(
    new URL("/v3/OS-FEDERATION/projects", auth_endpoint),
    {
      method: "GET",
      headers: {
        "X-Auth-Token": token,
      }
    }
  );

  if (resp.status != 200) {
    console.log("Could not retrieve projects");
  }

  const resp_projects = await resp.json();
  projects = resp_projects.projects.filter(project => project.enabled);

  return projects;
}


// Retrieve a scoped project token
export async function getScopedToken(token, project) {
  let scoped = "";
  
  const resp = await fetch(
    new URL("/v3/auth/tokens", auth_endpoint),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        auth: {
          identity: {
            methods: [
              "token"
            ],
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
    },
  );

  if (resp.status != 200 && resp.status != 201) {
    console.log("Could not retrieve a scoped token.");
    return scoped;
  }

  scoped = resp.headers.get("X-Subject-Token");

  // Cache the endpoint for object storage
  let login_meta = await resp.json();
  object_storage_endpoint =
    login_meta.token.catalog
    .filter(service => service.type === "object-store")[0]
    .endpoints
    .filter(endpoint => endpoint.interface === "public")[0]
    .url;

  console.log(object_storage_endpoint);

  return scoped;
}


// Retrieve ec2 credentials using the scoped project token
export async function getEC2Credentials(token, userId, projectId) {
  let ec2 = {};

  try {
    const resp = await fetch(
      new URL(`/v3/users/${userId}/credentials/OS-EC2`, auth_endpoint),
      {
        headers: {
          "X-Auth-Token": token,
        },
      },
    );

    const creds = await resp.json();
    ec2 = creds?.credentials?.find(credential => credential?.type === "ec2" && credential?.tenant_id === projectId);
    if (!ec2) {
      throw new Error("No credentials listed")
    }
  } catch (e) {
    console.log(e)
    console.log("Failed to retrieve EC2 credentials.");
    console.log("Trying to generate EC2 credentials.");

    const resp = await fetch(
      new URL(`/v3/users/${userId}/credentials/OS-EC2`),
      {
        headers: {
          "X-Auth-Token": token,
        },
        body: JSON.stringify({
          "tenant_id": projectId,
        }),
      },
    );

    const creds = await resp.json();
    ec2 = creds?.credential
  }

  console.log(ec2);

  return ec2;
}


export async function getBuckets(token) {
  let buckets = [];
  let marker = "";
  let bucket_page;

  do {
    try {
      const bucketURL = new URL("", object_storage_endpoint);
      // Use 100 as the bucket page limit
      bucketURL.searchParams.append("limit", 100);
      bucketURL.searchParams.append("format", "json")
      // Use the marker for paging the listings
      if (marker) {
        bucketURL.searchParams.append("marker", marker);
      }
      let resp = await fetch(bucketURL, {
        headers: {
          "X-Auth-Token": token,
        },
      });

      bucket_page = await resp.json();
      if (bucket_page.length > 0) buckets = [...buckets, ...bucket_page];
      marker = buckets[buckets.length - 1].name;
    } catch (e) {
      console.log(e);
      break;
    }
  } while (bucket_page?.length > 0);

  console.log(buckets);

  return buckets;
}


export async function getObjects(token, bucket) {
  let objects = [];
  let marker = "";
  let object_page;

  do {
    try {
      const objectURL = new URL(`/${bucket}`, object_storage_endpoint);
      // Use 1000 as the object page limit
      objectURL.searchParams("limit", 1000);
      bucketURL.searchParams("format", "json");
      // Use the marker for paging the listings
      if (marker) {
        objectURL.searchParams.append("marker", marker);
      }
      let resp = await fetch(objectURL, {
        headers: {
          "X-Auth-Token": token,
        },
      });

      object_page = await resp.json();
      if (object_page.length > 0) objects = [...objects, ...object_page];
      marker = objects[objects.length - 1].name;
    } catch (e) {
      console.log(e);
      break;
    }
  } while (object_page?.length > 0);

  console.log(objects);
  return objects;
}
