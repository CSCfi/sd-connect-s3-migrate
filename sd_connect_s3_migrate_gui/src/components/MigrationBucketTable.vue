<template>
  <c-data-table hide-footer :headers="headers" :data="tableData"></c-data-table>
</template>

<script setup>
import { computed } from "vue";
import { getBucketStatus, migrationStages } from "../scripts/common";
import { mdiPail } from "@mdi/js";

const { buckets, migrationStage } = defineProps({
  buckets: Array,
  migrationStage: {
    type: String,
    validator(value) {
      return !value || !!migrationStages[value];
    },
  },
});

const headers = [
  { key: "name", align: "center", value: "Name", sortable: false },
  { key: "status", value: "Conversion need", sortable: false },
  { key: "progress", align: "center", value: "", sortable: false },
];

const staticTableData = computed(() => {
  return buckets?.map((bucket) => {
    const status = getBucketStatus(bucket.conversionNeed);
    return {
      name: {
        value: null,
        children: [
          {
            value: null,
            component: {
              tag: "c-icon",
              params: {
                path: mdiPail,
                style: {
                  marginRight: "0.5rem",
                },
              },
            },
          },
          {
            value: bucket.name,
            component: {
              tag: "span",
            },
          },
        ],
      },
      status: status
        ? {
            value: status.value,
            component: {
              tag: "c-status",
              params: {
                type: status.type,
              },
            },
          }
        : { value: null },
    };
  });
});

/**
 * Display progress string dependent on migration stage
 * @param {Object} bucket - object describing the bucket
 */
function getProgressString(bucket) {
  if (bucket.currentlyMigrating === true) {
    switch (migrationStage) {
      case migrationStages.starting:
        return "Preparing for conversion...";
      case migrationStages.sharing:
        return "Converting sharing...";
      case migrationStages.headers:
        return "Preparing items for conversion...";
      case migrationStages.objects:
        return `${bucket.totalObjectsDone}/${bucket.totalObjects} items converted`;
    }
  } else if (bucket.sharingMigrated && bucket.headersMigrated && bucket.totalObjects === bucket.totalObjectsDone) {
    // For converted buckets, display the object stage string
    return `${bucket.totalObjectsDone}/${bucket.totalObjects} items converted`;
  } else {
    return "";
  }
}

const tableData = computed(() => {
  // No need to recompute all data
  return staticTableData.value?.map((row, i) => {
    const bucket = buckets[i];
    return {
      ...row,
      progress: migrationStage
        ? {
            value: getProgressString(bucket),
            component: {
              tag: "span",
              params: {
                style: {
                  // provide width to prevent row from visual glitch on update
                  minWidth: "35ch",
                },
              },
            },
          }
        : {
            value: `${bucket.totalObjectsDone}/${bucket.totalObjects} items converted`,
            component: {
              tag: "span",
            },
          },
    };
  });
});
</script>
<style></style>
