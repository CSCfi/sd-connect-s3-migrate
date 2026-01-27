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
          {{ bucket.name }} -> {{ convertBucketName(bucket.name) }} {{
            // Flag casese where bucket name is not changed in migration
            bucket.name === convertBucketName(bucket.name)
              ? "(no name change in migration)"
              : ""
          }}
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

// For transliterating to ASCII, seems like the best alternative
// Dependency audited in approx three hours on 26.1.2026, Signed: Sampsa Penna
import { slugify } from 'transliteration';
import { SD_CONNECT_API_URL } from '../scripts/config';


const {
  migrateBuckets,
  scopedToken,
} = defineProps([
  "migrateBuckets",
  "scopedToken",
]);

const emit = defineEmits([
  "bucketsMigrated",
]);

let totalObjects = ref(0);
let totalSize = ref(0);

let totalObjectsDone = ref(0);

let migrating = ref(false);

onMounted(() => {
  for (const bucket of migrateBuckets) {
    totalObjects.value += bucket.count;
    totalSize.value += bucket.bytes;
  }

  console.log(totalObjects.value);
  console.log(totalSize.value);
});

let ec2;

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

// Convert the bucket name to a compatible one with best effort
function convertBucketName(bucket) {
  // Convert to ascii slug, truncating to 63 characters
  let slug = slugify(`migrated-${bucket}`, {trim: true})
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
  return slug.toLowerCase();
}

// Copy over the bucket headers
async function migrateBucketHeaders(oldBucket, newBucket, objects) {
  if (!SD_CONNECT_API_URL) {
    console.log("No API URL provided, simulating header migration.");



    return;
  }
}

// Copy over the bucket contents
async function copyBucketContents(oldBucket, newBucket) {

}

async function beginMigration() {
  console.log("Begun migration.");

  // Iterate over all buckets flagged for migration
  for (const bucket of buckets) {

  }

  emit("bucketsMigrated");
}

</script>
