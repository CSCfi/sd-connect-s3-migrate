<template>

  <h2>Migrating buckets</h2>

  <div v-if="!migrating">
    <section>
      The UI will perform the following operations for objects within the selected buckets:
      <ul>
        <li>change the bucket name to a compatible one, truncating if necessary</li>
        <li>copy over the existing objects if required</li>
        <li>concatenate possible segmented objects into an s3 compatible object</li>
        <li>migrate the headers between buckets to preserve file access</li>
        <li>migrate possible shared access grants</li>
      </ul>
    </section>
  
    <section>
      The maximum amount of files to be migrated: {{ totalObjects }} (some files can be skipped if bucket name does not change).
    </section>
    <section>
      The maximum amount of data to be migrated: {{ getHumanReadableSize( totalSize, "en" ) }}
    </section>
  
    <section>
      The following buckets will be migrated:
      <ul>
        <li v-for="bucket in migrateBuckets">
          {{ bucket.value.name }} -> {{ convertBucketName(bucket.value.name) }} {{
            // Flag casese where bucket name is not changed in migration
            bucket.value.name === convertBucketName(bucket.value.name)
              ? "(no name change in migration)"
              : ""
          }}
          <ul v-if="bucket.value.currentlyMigrating">
            <li v-if="bucket.value.totalHeadersDone < bucket.value.totalHeaders">
              Migrating headers: {{ bucket.value.totalHeadersDone }} / {{ bucket.value.totalHeaders }} (migrating {{ bucket.value.currentlyMigratingFile }})
            </li>
            <li v-else-if="bucket.value.totalObjectsDone < bucket.value.totalObjects">
              Migrating files: {{ bucket.value.totalObjectsDone }} / {{ bucket.value.totalObjects }} (current file: {{ bucket.value.currentlyMigratingFile }})
            </li>
            <li v-else-if="!bucket.value.sharingMigrated">
              Migrating sharing
            </li>
            <li v-else>
              Migration done
            </li>
          </ul>
        </li>
      </ul>
    </section>

    <section>
      <c-button @click="beginMigration().then(console.log('Migration finished.'))">Begin migration</c-button>
    </section>
  </div>

  <div v-else>

    <h3>Migration progress</h3>
    <c-progress-bar :value="totalObjectsDone / totalObjects" />

  </div>

</template>

<script setup>
import { onMounted, ref } from 'vue';


// transliteration – selected for transliteration unicode to ASCII while
// minimizing the loss of meaning, seemed like the best alternative

// Dependency quickly audited in approx three hours on 26.1.2026, Signed: Sampsa Penna
import { slugify } from 'transliteration';
import { SD_CONNECT_API_URL } from '../scripts/config';
import { timeout } from '../scripts/common';
import { checkObjectManifest, getBucketACLs, getEC2Credentials, getObject, getObjectEtag, getObjectMeta, getObjects } from '../scripts/openstack';
import { BucketAccelerateStatus, CompleteMultipartUploadCommand, CreateBucketCommand, CreateMultipartUploadCommand, GetObjectOutputFilterSensitiveLog, HeadBucketCommand, HeadObjectCommand, PutBucketPolicyCommand, PutObjectCommand, S3Client, UploadPartCommand, UploadPartCopyCommand } from '@aws-sdk/client-s3';


const {
  buckets,
  scopedToken,
  projectId,
  s3address,
} = defineProps([
  "buckets",
  "scopedToken",
]);

const emit = defineEmits([
  "bucketsMigrated",
]);

let totalObjects = ref(0);
let totalSize = ref(0);

let totalObjectsDone = ref(0);

let migrating = ref(false);

/*
Migration process object definition

The bucket level object is wrapped into a ref() to make bucket updates render correctly.

[
  {
    name: str
    totalObjects: int
    totalObjectsDone: int
    totalHeaders: int
    totalHeadersDone: int
    currentlyMigrating: bool
    sharingMigrated: bool
    headersMigrated: bool
    currentlyMigratingFile: str
    objects: [
      {
        key: str
        headerDone: bool
        contentDone: bool
        isSegmented: bool
        manifestBackup: str
      },
    ],
  },
]
*/
let migrateBuckets = ref([]);

let ec2;
let client;

onMounted(() => {
  for (const bucket of buckets) {
    totalObjects.value += bucket.count;
    totalSize.value += bucket.bytes;

    migrateBuckets.value.push(ref({
      name: bucket.name,
      totalObjects: bucket.count,
      totalObjectsDone: 0,
      totalHeaders: bucket.count,
      totalHeadersDone: 0,
      currentlyMigrating: false,
      currentlyMigratingFile: "",
      sharingMigrated: false,
      objects: [],
    }));
  }

  console.log(totalObjects.value);
  console.log(totalSize.value);
  console.log(migrateBuckets.value);
});

/**
 * Get a human readable size of a bucket (copied over from SD Connect codebase)
 * @param {number} val - the size to parse
 * @param {string} locale - the locale to select correct decimal separator
 */
function getHumanReadableSize(val, locale) {
  const BYTE_UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];

  let size = val;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < BYTE_UNITS.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  const decimalSize = size.toFixed(1);
  let result = decimalSize.toString();

  if (locale === "fi") {
    result = result.replace(".", ",");
  }

  return `${result} ${BYTE_UNITS[unitIndex]}`;
}


/**
 * Convert the bucket name to a compatible one with best effort 
 * @param {string} bucket - the name of the bucket
 */
function convertBucketName(bucket) {
  // Convert to ascii slug, truncating to 63 characters
  let slug = slugify(`${bucket}`, {trim: true})
    .substring(0, 63);

  // If the slug ends in a dash, drop it
  if (slug[62] === "-") {
    slug = slug.substring(0, 62);
  }

  // If the slug contains underscores, replace them with a dash
  slug = slug.replaceAll("_", "-");
  // A full stop is also a possibility, but shouldn't be able to exist
  // in swift buckets anyway, not covering it for now

  // Return the lowercase version of the result
  slug = slug.toLowerCase();

  if (bucket == slug) return slug;
  else return `migrated-${slug}`;
}


/**
 * Migrate bucket object headers under the s3 compatible bucket name
 * @param {Object} bucket - object describing the bucket to be migrated
 * @param {string} bucket.value.name - the name of the bucket to be migrated
 * @param {string} bucket.value.currentlyMigratingFile - reference to file currently being migrated
 * @param {Object[]} bucket.value.objects - array of the bucket objects
 * @param {string} bucket.value.objects[].key - name of the object in question
 * @param {boolean} bucket.value.objects[].headerDone - status of header migration for the object
 */
async function migrateBucketHeaders(bucket) {
  // Skip header copy if the bucket name doesn't change
  if (bucket.value.name == convertBucketName(bucket.value.name)) {
    for (const object of bucket.value.objects) {
      object.headerDone = true;
    }
    return;
  }

  // Simulate header migration if there's no SD Connect API URL
  // We're first testing just the object storage side of things, as it's preferable
  // to test header migration on dev before starting to migrate production headers
  if (!SD_CONNECT_API_URL) {
    console.log("No API URL provided, simulating header migration.");

    for (const object of bucket.value.objects) {
      bucket.value.currentlyMigratingFile = object.key;
      await timeout(50);
      object.headerDone = true;
    }

    return;
  }
  
  // Migrate bucket headers for objects that require it
  for (const object of bucket.value.objects) {
    // Skip potentially done objects to continue from saved migration state
    if (object.headerDone) continue;
  }

  // TODO: actual header migration
}

/**
 * 
 * @param {string} bucket - the name of the bucket the object is in
 * @param {string} key - the key of the object to be copied
 * @param {string} manifest - the DLO manifest of the object from swift side
 */
async function multipartCopyObject(bucket, key, manifest) {
  // Split the manifest to a bucket and prefix part
  let segment_bucket = manifest.slice(0, manifest.indexOf("/"));
  let segment_prefix = manifest.slice(manifest.indexOf("/") + 1);

  // Retrieve a list of the current object segments
  const segments = await getObjects(scopedToken, segment_bucket, segment_prefix);
  console.log(segments);

  // Copy the segments as multipart parts
  const startMultipart = new CreateMultipartUploadCommand({
    Bucket: convertBucketName(bucket),
    Key: key,
  });
  // Get the upload id
  const multipartResp = await client.send(startMultipart);
  const uploadId = multipartResp?.uploadId;
  if (!uploadId) return;

  // Cache for the multipart parts
  let multipartParts = [];

  for (const segment of segments) {
    const multipartCopyCommand = new UploadPartCopyCommand({
      Bucket: convertBucketName(bucket),
      CopySource: `${segment_bucket}/${segment.name}`,
      Key: key,
      // SD Connect default object is signified by 8 digits, use that as part number
      PartNumber: Number(segment.name.match(/[0-9]{8}/)[0]),
      UploadId: uploadId,
    });
    const partCopyResp = await client.send(multipartCopyCommand);

    // Check that the checksums match with the part and original
    console.log(partCopyResp?.Etag);
    console.log(await getObjectEtag(scopedToken, segment_bucket, segment.name));

    multipartParts.push({
      ETag: partCopyResp?.Etag,
      PartNumber: Number(segment.name.match(/[0-9]{8}/)[0]),
    });
  }

  // Finish the multipart copy
  const finishMultipart = new CompleteMultipartUploadCommand({
    Bucket: convertBucketName(bucket),
    Key: key,
    MultipartUpload: {
      Parts: multipartParts,
      UploadId: uploadId,
    },
  });
  const finishMultipartResponse = await client.send(finishMultipart);
  console.log(finishMultipartResponse);
}

/**
 * 
 * @param {string} bucket - the name of the bucket the object is in
 * @param {string} key - the key of the object to be copied
 */
async function conventionalCopyObject(bucket, key) {
  let objectMeta = await getObjectMeta(scopedToken, bucket, key);

  // If the object is smaller than 200 MiB, copy it as a single object
  if (objectMeta.size > 200 * 1024 * 1024) {
    let object = await getObject(scopedToken, bucket, key);

    try {
      const putObject = new PutObjectCommand({
        Body: object,
        Bucket: convertBucketName(bucket),
        Key: key,
      });
      const putObjectResp = await client.send(putObject);
      console.log(putObjectResp);
    } catch (e) {
      console.log(e)
    }

    return;
  }

  // Otherwise, copy object in 100 MiB parts using s3 multipart
  const startMultipart = new CreateMultipartUploadCommand({
    Bucket: convertBucketName(bucket),
    Key: key,
  });
  // Get the upload id
  const multipartResp = await client.send(startMultipart);
  const uploadId = multipartResp?.uploadId;
  if (!uploadId) return;

  // Cache for the multipart parts
  let multipartParts = [];
  let partNumber = 0;

  for (let i = 0; i < objectMeta.size; i = i + 100 * 1024 * 1024) {
    // Get the next 100 MiB of the object (using inclusive range)
    let object = await getObject(scopedToken, bucket, key, i, i + 100 * 1024 * 1024 - 1);

    try {
      const putObjectPart = new UploadPartCommand({
        Body: object,
        Bucket: convertBucketName(bucket),
        Key: key,
        PartNumber: partNumber,
        uploadId: uploadId,
      });
      const multipartPartResp = await client.send(putObjectPart);
      multipartParts.push({
        ETag: multipartPartResp?.ETag,
        PartNumber: partNumber,
      });
      partNumber++;
    } catch (e)  {
      console.log(e);
    }
  }

  // Finish the multipart copy
  const finishMultipart = new CompleteMultipartUploadCommand({
    Bucket: convertBucketName(bucket),
    Key: key,
    MultipartUpload: {
      Parts: multipartParts,
      UploadId: uploadId,
    },
  });
  const finishMultipartResponse = await client.send(finishMultipart);
  console.log(finishMultipartResponse);
}

/**
 * Copy over the bucket objects for objects that require it
 * @param {Object} bucket - object describing the bucket to be migrated
 * @param {string} bucket.value.name - the name of the bucket to be migrated
 * @param {string} bucket.value.currentlyMigratingFile - reference to file currently being migrated
 * @param {Object[]} bucket.value.objects - array of the bucket objects
 * @param {string} bucket.value.objects[].key - name of the object in question
 * @param {boolean} bucket.value.objects[].contentDone - status of header migration for the object
 */
async function migrateBucketObjects(bucket) {
  // Migrate bucket objects for objects that require it
  for (const object of bucket.value.objects) {
    // Skip potentially done objects to continue from saved migration state
    if (object.contentDone) continue;
    // Skip objects that are just SD Connect v1 segments
    if (object.key.match(".segments")) continue;

    /*
    We work on the basis that if the object is empty in the listing, it's
    been uploaded using the v2 SD Connect. This is most likely the case, as
    v2 SD Connect only uses dynamic large objects. Static large objects have
    a size in the object listing, so they won't be correctly identified as
    incompatible for now. In case we require this functionality for Allas
    objects (at least allas cli uses SLO) it can be implemented later.
    Alternatively we can add the option to force migration under a new bucket
    name to avoid having to check this.

    The object copy process tries to preserve bandidth by using hardware copy
    whenever possible, and goes as follows:

      1. Check if the object needs to be copied
      2. Check if the bucket name changes
        - if bucket name doesn't change, store the object manifest for safekeeping,
          needed to allow reverting back to the old object version if something
          fails.
        - if the bucket name changes, we don't need to care about the manifest
      3. Copy the object (use hardware copy as long as possible to avoid consuming
         bandwidth)
        - In case the object is segmented, copy using multipart with the segments
          as the source
        - In case the object is not segmented, copy as a standard object
        - In case the bucket can't be accessed via S3 API even in legacy mode,
          copy by proxying the object through user's machine
    */
    
    let copyNeeded = false;
    // If the bucket name changes we need to copy the object
    if (bucket.value.name != convertBucketName(bucket.value.name)) copyNeeded = true;
    // If the object is segmented we need to copy the object
    let manifest = await checkObjectManifest(scopedToken, bucket.value.name, object.key);
    if (manifest) copyNeeded = true;
    
    // Skip copying the object if it need not be copied
    if (!copyNeeded) continue;

    // Display the currently migrated file
    bucket.value.currentlyMigratingFile = object.key;

    // Start the migration
    try {
      // If the object can be accessed using S3 API, perform the copy using multipart
      const objectAccessCommand = new HeadObjectCommand({
        Bucket: bucket.value.name,
        Key: object.key,
      });
      try {
        await client.send(objectAccessCommand);
        await multipartCopyObject(bucket.value.name, object.key, manifest);
      } catch (e) {
        console.log(e);
        // If the object is inaccessible using S3 API, copy converntionally
        await conventionalCopyObject(bucket.value.name, object.key);
      }

      object.contentDone = true;
    } catch (e) {
      console.log(e)
      // In case we fail migration, and the bucket name doesn't change, revert to manifest
      // TODO: revert to previous manifest
    }
  }
}

/**
 * Copy over the bucket sharing if that's required
 * @param {Object} bucket - the bucket that is to be migrated
 * @param {string} bucket.name - the name of the bucket that is to be migrated
 */
async function migrateBucketSharing(bucket) {
  let ACLs = {};
  // Currently we assume there are no bucket policies present
  // TODO: do we want to check if they exist?
  let policy = {
    "Version": "2012-10-17",
    "Statement": [],
  };
  // Retrieve the bucket ACLs
  ACLs = await getBucketACLs(bucket.name);
  // Add statements for all read rights
  if (ACLs?.read?.length > 0) {
    for (const project of ACLs.read) {
      let newStatement = {
        "Sid": "GrantSDConnectSharedAccessToProject",
        "Effect": "Allow",
        "Principal": {
          "AWS": `arn:aws:iam::${project}:root`,
        },
        "Actions": [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetObjectTagging",
          "s3:GetObjectVersion",
          ...(
            // If the project exists in the write ACL, also add the write statements.
            // We don't sync bare write rights as non-supported.
            ACLs.write.findIndex(i => i == project) >= 0
            ? [
              "s3:PutObject",
              "s3:DeleteObject",
              "s3:AbortMultipartUpload",
              "s3:ListMultipartUploadParts",
              "s3:ListBucketMultipartUploads",
            ] : []
          )
        ],
        "Resource": [`arn:aws:s3:::${convertBucketName(bucket.name)}`, `arn:aws:s3:::${convertBucketName(bucket.name)}/*`],
      }

      // Append the new statement to the list of statements
      policy.Statement.push(newStatement);
    }
  }
  try {
    const command = new PutBucketPolicyCommand({
      Bucket: convertBucketName(bucket.name),
      Policy: JSON.stringify(policy),
    });
    await client.send(command);
    console.log(`Added bucket policy for ${convertBucketName(bucket.name)}`);
  } catch (e) {
    if (
      e instanceof S3ServiceException &&
      e.name === "MalformedPolicy"
    ) {
      // Shamelessly recycle the error handling from AWS docs
      console.error(
        `Error from S3 while setting the bucket policy for the bucket "${convertBucketName(bucket.name)}". The policy was malformed.`,
      );
      return;
    } else if (caught instanceof S3ServiceException) {
      console.error(
        `Error from S3 while setting the bucket policy for the bucket "${convertBucketName(bucket.name)}". ${caught.name}: ${caught.message}`,
      );
    } else {
      throw caught;
    }
  }

  // If the bucket name has changed, we need to migrate the Vault side sharing
  // info as well
  if (bucket.name == convertBucketName(bucket.name)) return;
  // If we don't have API access configured, skip the operation Vault share migrate
  if (!SD_CONNECT_API_URL) return;
  // TODO: implement Vault sharing
}

/**
 * Create the new bucket if the bucket name changes
 * @param {string} bucket - name of the old bucket
 */
async function createNewBucket(bucket) {
  if (bucket != convertBucketName(bucket)) {
    // Check if the bucket already exists and we have access
    try {
      const headBucket = new HeadBucketCommand({
        Bucket: convertBucketName(bucket),
      });
      const resp = await client.send(headBucket);
      return;
    } catch(e) {
      console.log(e);
    }

    // The bucket didn't exist yet, try to create it
    const createBucket = new CreateBucketCommand({
      Bucket: convertBucketName(bucket),
    });
    await client.send(createBucket);
  }
}

/**
 * Start the migration process for selected buckets
 */
async function beginMigration() {
  console.log("Begun migration.");

  // Initialize the ec2 credentials and the client
  ec2 = await getEC2Credentials(scopedToken, projectId);
  client = new S3Client({
    region: "us-east-1",
    endpoint: s3address,
    credentials: {
      accessKeyId: ec2.access,
      secretAccessKey: ec2.secret,
    },
  })

  // Iterate over all buckets flagged for migration
  for (const bucket of migrateBuckets.value) {
    // Retrieve the list of bucket objects
    let objects = await getObjects(scopedToken, bucket.value.name);
    // Format the object listing according to our requirements
    migrateBuckets.value.objects =
      objects.map(object => {
        return {
          key: object.name,
          headerDone: false,
          contentDone: false,
          isSegmented: object.bytes == 0 ? true : false,
          manifestBackup: "",
        };
      });

    // Flag the bucket as actively migrated
    bucket.value.currentlyMigrating = true;

    // Ensure that the bucket exists
    try {
      await createNewBucket(bucket.value.name);
    } catch (e) {
      console.log("Failed to create the new bucket after bucket name change. Reason/traceback:");
      console.log(e);
    }

    // Migrate bucket headers
    try {
      await migrateBucketHeaders(bucket);
    } catch (e) {
      console.log("Bucket header migration failed. Reason/traceback:");
      console.log(e);
    }

    // Migrate bucket contents
    try {
      await migrateBucketObjects(bucket);
    } catch (e) {
      console.log("Bucket objects migration failed. Reason/traceback:");
      console.log(e);
    }

    // Migrate bucket sharing
    try {
      await migrateBucketSharing(bucket);
    } catch (e) {
      console.log("Bucket sharing migration failed. Reason/traceback:");
      console.log(e);
    }
  }

  // Emit the migrate process state after finalize
  emit("bucketsMigrated", migrateBuckets);
}

</script>
