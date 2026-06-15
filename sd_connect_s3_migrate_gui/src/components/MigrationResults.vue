<template>
  <div class="step-content">
    <p>
      <b>Project:</b>
      {{ project?.name }}
    </p>
    <h1>Data conversion is complete</h1>
    <c-alert type="error" v-if="alert === 'match'">
      <c-row gap="100" justify="space-between" align="center">
        <div class="alert-text">
          Your buckets have been copied and converted to be compatible with the current SD Connect version. Please take
          a moment to review the sizes and items to make sure they match before and after the conversion.
          <ul>
            <li>
              If everything matches, click
              <b>Match.</b>
            </li>
            <li>If you notice any differences, contact servicedesk@csc.fi with the subject "Sensitive data".</li>
          </ul>
        </div>
        <div class="actions">
          <c-button href="mailto:servicedesk@csc.fi?subject=Sensitive%20data" :target="null" outlined>
            Contact Service Desk
          </c-button>
          <c-button @click="alert = 'delete'">Match</c-button>
        </div>
      </c-row>
    </c-alert>
    <c-alert type="error" v-if="alert === 'delete'">
      <c-row gap="100" justify="space-between" align="center">
        <p class="alert-text">Would you like to delete the original incompatible buckets now?</p>
        <div class="actions">
          <c-button outlined @click="dismissAlert">Keep</c-button>
          <c-button @click="onDelete" :loading="deleting">Delete</c-button>
        </div>
      </c-row>
    </c-alert>
    <div v-if="deleteSuccess === true">
      <c-alert type="success">Original incompatible buckets were deleted successfully.</c-alert>
    </div>
    <div v-if="deleteSuccess === false">
      <c-alert type="error">
        Error deleting original incompatible data
        {{ errorBuckets.length ? `in bucket${errorBuckets.length > 1 ? "s" : ""} ${errorBuckets.join(", ")}` : "" }}.
      </c-alert>
    </div>
    <c-data-table hide-footer :headers="headers" :data="tableData"></c-data-table>
    <c-row v-if="alert === ''" gap="16" justify="end">
      <c-button @click="quit" outlined>Close application</c-button>
      <c-button @click="startConversion">Start new conversion</c-button>
    </c-row>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { ListObjectsV2Command } from "@aws-sdk/client-s3";
import { getReadableSize, getSegmentsPrefix, getTimestamp } from "../scripts/common";
import { getObjects, deleteBucket, deleteObject } from "../scripts/openstack";

const { project, migratedBuckets, scopedToken, s3client } = defineProps([
  "project",
  "migratedBuckets",
  "scopedToken",
  "s3client",
]);
const emit = defineEmits(["start-new-conversion"]);

const alert = ref("match");
const deleteSuccess = ref();
const deleting = ref(false);
const errorBuckets = ref([]);

async function onDelete() {
  if (deleting.value) return;
  try {
    deleting.value = true;
    errorBuckets.value = await deleteMigrated(migratedBuckets);
    deleteSuccess.value = errorBuckets.value.length ? false : true;
  } catch (e) {
    deleteSuccess.value = false;
    console.error("Failed to delete incompatible buckets. Reason/traceback:");
    console.error(e);
  }
  deleting.value = false;
  alert.value = "";
}
function dismissAlert() {
  if (deleting.value) return;
  alert.value = "";
}
function quit() {
  window.close();
}
function startConversion() {
  emit("start-new-conversion");
}

/**
 * Verifies and deletes migrated objects from source buckets, including their
 * associated segment objects and optional segment buckets
 *
 * @param {Array<Object>} buckets - list of buckets to process
 * @param {string} buckets[].name - source bucket name
 * @param {string} buckets[].convertedName - target S3 bucket name
 * @returns {Promise<Array<string>>} array of bucket names that encountered errors
 */
async function deleteMigrated(buckets) {
  // Primitive verification/deletion error tracking
  const errorSet = new Set();

  for (const bucket of buckets) {
    const bucketDeletionNeeded = bucket.name !== bucket.convertedName;
    const segmentsBucket = `${bucket.name}_segments`;
    const objects = bucket.objects;
    let segments = [];

    if (objects.length) {
      console.log(`Verifying and deleting ${objects.length} objects in ${bucket.name}`);

      // Get segments: might not exist if source bucket created with S3
      segments = await getObjects(scopedToken, segmentsBucket);
      // Map segments by prefix for verification and deletion
      const segmentsMap = new Map();
      segments.forEach((segment) => {
        const i = segment.name.lastIndexOf("/");
        const prefix = segment.name.slice(0, i + 1);
        const setSegments = segmentsMap.get(prefix);
        if (!setSegments) {
          segmentsMap.set(prefix, [segment.name]);
        } else {
          setSegments.push(segment.name);
        }
      });

      // Get converted objects
      let s3Objects;
      try {
        const listObjectsCmd = new ListObjectsV2Command({
          Bucket: bucket.convertedName,
        });
        const listObjectsResp = await s3client.send(listObjectsCmd);
        s3Objects = listObjectsResp?.Contents || [];
      } catch (e) {
        console.error(`Could not retrieve migrated objects from ${bucket.convertedName}`);
        console.error(e);
        errorSet.add(bucket.name);
        // Bucket and objects not deleted
        continue;
      }

      // Verify objects
      const objectsOk = await verifyObjects(scopedToken, bucket, objects, s3Objects, segmentsMap);
      if (!objectsOk) {
        errorSet.add(bucket.name);
        continue;
      }

      // Delete objects and segments
      const objectsDeleted = await deleteObjects(scopedToken, bucket, objects, segmentsMap);
      if (!objectsDeleted) {
        errorSet.add(bucket.name);
        continue;
      }
    } else {
      console.log(`No objects to delete in ${bucket.name}`);
    }

    // DELETE BUCKET if no previous errors
    if (errorSet.has(bucket.name)) continue;

    if (bucketDeletionNeeded) {
      const success = await deleteBucket(scopedToken, bucket.name);
      if (!success) errorSet.add(bucket.name);
    } else {
      console.log(`Bucket ${bucket.name} not deleted: it is the target bucket`);
    }
    // DELETE SEGMENTS BUCKET
    if (segments.length) {
      // Might fail in case of orphaned segments
      const success = await deleteBucket(scopedToken, segmentsBucket);
      if (!success) errorSet.add(bucket.name);
    }
  }
  return Array.from(errorSet);
}

/**
 * Verifies that a set of source objects have been correctly migrated to S3
 * and that associated metadata and segment information is consistent
 *
 * @param {string} scopedToken - token used for Swift API access
 * @param {Object} bucket - bucket metadata
 * @param {Array<Object>} objects - list of source objects to verify
 * @param {Array<Object>} s3Objects - list of objects from the target S3 bucket
 * @param {Map<string, Array>} segmentsMap - map of segment prefixes to segment object lists
 * @returns {Promise<boolean>} true if all objects pass verification, otherwise false
 */
async function verifyObjects(scopedToken, bucket, objects, s3Objects, segmentsMap) {
  // Create a map of S3 objects
  const s3ObjectMap = new Map(s3Objects.map((obj) => [obj.Key, obj]));

  const bucketDeletionNeeded = bucket.name !== bucket.convertedName;
  const swiftObjects = bucketDeletionNeeded ? await getObjects(scopedToken, bucket.name) : [];
  const swiftObjectMap = new Map(swiftObjects.map((obj) => [obj.name, obj]));

  for (const object of objects) {
    const s3Object = s3ObjectMap.get(object.key);
    // VERIFY: migrated object exists
    if (!s3Object) {
      console.error(`Object ${object.key} not found in target bucket ${bucket.convertedName}.`);
      return false;
    }

    // VERIFY: size of original and migrated object match (multipartUpload finalized properly)
    if (object.bytes !== s3Object.Size) {
      console.error(
        `Size mismatch in ${bucket.name} object ${object.key}: source ${object.bytes}, target ${s3Object.Size}`,
      );
      return false;
    }

    // VERIFY: last modified of source bucket object matches the one captured pre-migration
    if (bucketDeletionNeeded) {
      const swiftObject = swiftObjectMap.get(object.key);
      if (!swiftObject?.last_modified) {
        console.error(`Source object ${object.key} could not be retrieved from listing.`);
        return false;
      }
      const lastModified = getTimestamp(swiftObject.last_modified);
      if (lastModified !== object.lastModified) {
        console.error(`Source object ${object.key} last modified does not match.`);
        return false;
      }
    }

    // VERIFY: segments corresponding to manifest prefix exist
    if (object.isSegmented) {
      const segmentsPrefix = getSegmentsPrefix(object.manifestBackup);
      if (!segmentsPrefix) {
        console.error(`Segmented object ${object.key} is missing a manifest backup`);
        return false;
      }
      // Find objects with same prefix (objectName/uploadId) in segments map
      const foundSegments = segmentsMap.get(segmentsPrefix);
      if (!foundSegments) {
        console.error(`No segments with prefix ${segmentsPrefix} found in segment listing`);
        return false;
      }
    }
  }
  return true;
}

/**
 * Deletes migrated objects from the source bucket and deletes associated segment objects
 *
 * @param {string} scopedToken - token used for Swift API access
 * @param {Object} bucket - bucket metadata
 * @param {Array<Object>} objects - list of source objects to delete
 * @param {Map<string, Array>} segmentsMap - map of segment prefixes to segment object lists
 * @returns {Promise<boolean>} True if all deletions succeeded, otherwise false
 */
async function deleteObjects(scopedToken, bucket, objects, segmentsMap) {
  let objectsDeleted = true;
  const bucketDeletionNeeded = bucket.name !== bucket.convertedName;
  const segmentsBucket = `${bucket.name}_segments`;

  for (const object of objects) {
    // Delete object (manifest)
    if (bucketDeletionNeeded) {
      // Delete object in the source bucket
      console.log(`Deleting object ${object.key}`);
      const deleted = await deleteObject(scopedToken, bucket.name, object.key);
      if (!deleted) {
        objectsDeleted = false;
        continue;
      }
    } else {
      console.log(`Object ${object.key} will not be deleted: it is the target object`);
    }

    // Delete object segments
    if (object.isSegmented) {
      const segmentsPrefix = getSegmentsPrefix(object.manifestBackup);
      const foundSegments = segmentsMap.get(segmentsPrefix);
      console.log(`Found ${foundSegments.length} segment(s) with prefix ${segmentsPrefix} to delete`);
      for (const segment of foundSegments) {
        const deleted = await deleteObject(scopedToken, segmentsBucket, segment);
        if (!deleted) {
          objectsDeleted = false;
        }
      }
    }
  }
  return objectsDeleted;
}

/* TABLE */
const headers = [
  { key: "name_before", align: "center", value: "Name before", sortable: false },
  { key: "name_after", align: "center", value: "Name after", sortable: false },
  { key: "size_before", align: "center", value: "Size before", sortable: false },
  { key: "size_after", align: "center", value: "Size after", sortable: false },
  { key: "items_before", align: "center", value: "Items before", sortable: false },
  { key: "items_after", align: "center", value: "Items after", sortable: false },
];

const tableData = computed(() => {
  return migratedBuckets.map((bucket) => {
    return {
      name_before: {
        value: bucket.name,
      },
      name_after: {
        value: bucket.convertedName,
      },
      size_before: {
        value: getReadableSize(bucket.bytes),
      },
      size_after: {
        value: getReadableSize(bucket.bytesDone),
      },
      items_before: {
        value: bucket.totalObjects,
      },
      items_after: {
        value: bucket.totalObjectsDone,
      },
    };
  });
});
</script>
<style scoped>
.step-content > div,
.step-content > c-row {
  margin-top: 2rem;
}
.alert-text {
  margin-top: 0;
  flex: 1;
}
.actions > * {
  margin-right: 1rem;
}
</style>
