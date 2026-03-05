<template>
  <div>
    <p>
      <b>Project:</b>
      {{ project?.name }} {{ project?.description }}
    </p>
    <h1>Select buckets to convert</h1>
    <p>
      Select buckets you want to convert. Note that conversion can take a lot of time depending on your internet
      connection. We recommend deleting unneeded files and buckets from SD Connect before starting conversion as this
      shortens conversion time.
    </p>
    <!--TODO add link when it exists-->
    <c-link underline href="#" target="_blank">
      See detailed instructions
      <c-icon :path="mdiOpenInNew" />
    </c-link>
    <c-data-table
      selectable
      hide-footer
      no-data-text="There are no buckets in the seleted project"
      :headers="headers"
      :data="tableData"
      @selection="handleSelect"
      selection-property="bucket"
    ></c-data-table>
    <div class="alert-wrapper">
      <c-alert v-if="selected.length" type="warning">
        <span>
          <b>Estimated conversion time:</b>
          {{ getReadableTime(estimatedTime) }}
        </span>
        <c-link underline href="#" target="_blank">
          See detailed instructions
          <c-icon :path="mdiOpenInNew" />
        </c-link>
      </c-alert>
    </div>
    <div class="alert-wrapper">
      <c-alert v-if="selected.length" type="warning">
        <span>
          <b>Quota needed to complete conversion:</b>
          {{ getReadableSize(quotaNeeded) }}
        </span>
        Please check that your project has enough storage quota to proceed with the conversion from my.csc.fi.
        <c-link underline href="#" target="_blank">
          See detailed instructions
          <c-icon :path="mdiOpenInNew" />
        </c-link>
      </c-alert>
    </div>
    <c-row justify="space-between">
      <c-button outlined @click="emitBack" @keyup.enter="emitBack">Cancel</c-button>
      <c-button @click="selectBuckets" @keyup.enter="selectBuckets">Start conversion</c-button>
    </c-row>
    <c-toasts id="select-bucket-toasts"></c-toasts>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { mdiOpenInNew, mdiPail } from "@mdi/js";
import { getReadableSize, getReadableTime } from "../scripts/common";
import { getBuckets } from "../scripts/openstack";

const { project, scopedToken } = defineProps(["project", "scopedToken"]);

const emit = defineEmits(["selectBuckets", "goBack"]);

function selectBuckets() {
  if (!selected.value.length) {
    addToast("error", "Please select buckets to convert");
    return;
  }
  emit("selectBuckets", selected.value);
}

function emitBack() {
  emit("goBack");
}

function addToast(type, msg) {
  const toast = {
    type: type,
    message: msg,
  };
  document.getElementById("select-bucket-toasts").addToast(toast);
}

/** TABLE */
const bytesSec = (100 * 1000000) / 8;

let buckets = ref([]);
let selected = ref([]);

const headers = [
  { key: "name", align: "center", value: "Name", sortable: false },
  { key: "status", value: "Conversion need", sortable: false },
];

onMounted(() => {
  console.log(`Using scoped token: ${scopedToken}`);
  getBuckets(scopedToken).then((ret) => {
    buckets.value = ret;
  });
});

const tableData = computed(() => {
  return buckets.value
    .filter((bucket) => !bucket.name.match("_segments"))
    .map((bucket) => {
      const status = getBucketStatus(bucket);
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
        status: {
          value: status.value,
          component: {
            tag: "c-status",
            params: {
              type: status.type,
            },
          },
        },
        // keep bucket object in table data to simplify selection addition/removal
        bucket: {
          value: bucket,
        },
      };
    });
});

const quotaNeeded = computed(() => {
  return selected.value.reduce((quota, bucket) => {
    if (bucket.count && bucket.bytes === 0) {
      // get bytes from segments bucket
      const segments = buckets.value.find((b) => b.name === `${bucket.name}_segments`);
      if (segments?.bytes) return quota + segments.bytes;
    } else {
      return quota + bucket.bytes;
    }
  }, 0);
});

const estimatedTime = computed(() => {
  return Math.round(quotaNeeded.value / bytesSec);
});

// Add a bucket to the selected bucket listing
function handleSelect(event) {
  selected.value = event.detail;
}

// Determine the recommended action for the bucket
function getRecommendedAction(bucket) {
  function isLowerCaseOrNum(char) {
    return /[\p{L}0-9]/u.test(char) && char === char.toLowerCase();
  }
  // If the bucket contains whitespace, it's guaranteed to break S3
  if (/[\s]/u.test(bucket.name)) {
    return 5;
  }

  // If the bucket doesn't have any bytes, but has content, it has likely
  // been filled with swift large objects
  if (!bucket.bytes && bucket.count) {
    return 4;
  }

  // If the bucket has a matching segemnts bucket with content, it likely
  // contains swift large objects
  if (buckets.value.find((nb) => nb.name == `${bucket.name}_segments`)?.count > 0) {
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

function getBucketStatus(bucket) {
  const statusNum = getRecommendedAction(bucket);
  if (statusNum < 5) {
    return { type: "warning", value: "Optional" };
  }
  return { type: "error", value: "Must" };
}
</script>
<style scoped>
c-row {
  margin-top: 2rem;
}
c-data-table {
  margin-top: 1rem;
  --c-data-table-highlighted-column-background-color: var(--c-white);
  --c-icon-color: var(--c-primary-600);
}
.alert-wrapper {
  margin: 1rem 0;
}
</style>
