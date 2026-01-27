<template>

<div
  class="grid gap-4"
>
  <c-table ref="tableElementRef" responsive>
    <table>
      <thead>
        <tr>
          <th v-for="header in headers" :key="header">{{ header }}</th>
        </tr>
      </thead>

      <tbody>
        <tr v-if="renderBuckets.length == 0" no-mobile-labels>
          <td colspan="4">
            <div class="grid place-content-center p-4 gap-4">
              No buckets found in project
            </div>
          </td>
        </tr>

        <tr v-for="bucket in renderBuckets" :key="bucket.id">
          <td>{{ bucket.name }}</td>

          <td>{{ bucket.count }}</td>

          <td>
            <c-status
              v-if="getRecommendedAction(bucket) == 0"
              type="success"
            >
              May not need migration
            </c-status>
            <c-status
              v-else-if="getRecommendedAction(bucket) > 3"
              type="error"
            >
              Needs migration: {{ getRecommendedAction(bucket) == 4 ? "contains whitespace" : "contains incompatible objects" }}
            </c-status>
            <c-status
              v-else
              type="warning"
            >
              May need migration: contains incompatible characters
            </c-status>
          </td>

          <td class="text-right">
            <c-checkbox
              @changeValue="checkSelected(bucket) ? removeFromSelected(bucket) : addToSelected(bucket)"
              :checked="checkSelected(bucket)"
            >
              Select for migration
            </c-checkbox>
          </td>
        </tr>
      </tbody>
    </table>

    <c-button class="justify-self-start" @click="selectBuckets">
      Migrate buckets
    </c-button>
  </c-table>

</div>

</template>

<script setup>
import { onMounted, ref, render, watch } from 'vue';
import { getBuckets } from '../scripts/openstack';


const {
  scopedToken,
} = defineProps([
  "scopedToken",
]);

const emit = defineEmits([
  "selectBuckets",
]);

const headers = ["Name", "Objects", "Recommended action", "Migrate"];

let buckets = [];
let renderBuckets = ref([]);
let selected = ref([]);

onMounted(() => {
  console.log(`Using scoped token: ${scopedToken}`);
  getBuckets(scopedToken).then(ret => {
    buckets = ret;
    renderBuckets.value = buckets.filter(bucket => !bucket.name.match("_segments"));
  });
});

// Check if a bucket is selected from the listing
function checkSelected(bucket) {
  return selected.value.find(i => i.name == bucket.name);
}

// Add a bucket to the selected bucket listing
function addToSelected(bucket) {
  selected.value = [
    ...selected.value,
    bucket,
  ];
}

// Remove a bucket from the selected bucket listing
function removeFromSelected(bucket) {
  selected.value = [
    ...selected.value.filter(item => item.name === bucket.name),
  ];
}

// Emit selected buckets to the main app
function selectBuckets() {
  emit("selectBuckets", Array.from(selected.value));
}

// Determine the recommended action for the bucket
function getRecommendedAction(bucket) {
  function isLowerCaseOrNum(char) {
    return /[\p{L}0-9]/u.test(char) && char === char.toLowerCase();
  }

  // If the bucket doesn't have any bytes, but has content, it has likely
  // been filled with swift large objects
  if (!bucket.bytes && bucket.count) {
    return 5;
  }

  // If the bucket has a matching segemnts bucket with content, it likely
  // contains swift large objects
  if (buckets.find(nb => nb.name == `${bucket.name}_segments`)?.count > 0) {
    return 5;
  }

  // If the bucket contains whitespace, it's guaranteed to break S3
  if (/[\s]/u.test(bucket.name)) {
    return 4;
  }

  // If the bucket name is too long, it will likely have to be truncated
  if (bucket.name.length < 3 || bucket.name.length > 63) {
    return 3;
  }

  // If the bucket doesn't start with lowercase alphanumeric, it should
  // probably be migrated
  if (!isLowerCaseOrNum(bucket.name[0]) || !isLowerCaseOrNum(bucket.name[bucket.name.length - 1])) {
    return 2;
  }

  // If the bucket contains non-alphanumeric characters, it should probably
  // be migrated with a conforming name
  if (!bucket.name.match(/^[a-z0-9-]+$/g)) {
    return 1;
  }

  return 0;
}

</script>
