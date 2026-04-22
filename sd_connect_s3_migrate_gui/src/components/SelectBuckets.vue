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
    <c-link
      underline
      href="https://docs.csc.fi/data/sensitive-data/sd-connect-conversion-tool-ui/#34-select-buckets-to-convert"
      target="_blank"
    >
      See detailed instructions
      <c-icon :path="mdiOpenInNew" />
    </c-link>
    <c-data-table
      selectable
      hide-footer
      no-data-text="There are no buckets in the selected project"
      :headers="headers"
      :data="tableData"
      @selection="handleSelect"
      selection-property="bucket"
      :key="tableKey"
      :loading="loading"
    ></c-data-table>
    <div class="alert-wrapper">
      <c-alert v-if="selected.length" type="warning">
        <span>
          <b>Estimated conversion time:</b>
          {{ getReadableTime(estimatedTime) }}
        </span>
        <c-link
          underline
          href="https://docs.csc.fi/data/sensitive-data/sd-connect-conversion-tool-ui/#34-select-buckets-to-convert"
          target="_blank"
        >
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
        <c-link
          underline
          href="https://docs.csc.fi/data/sensitive-data/sd-connect-conversion-tool-ui/#34-select-buckets-to-convert"
          target="_blank"
        >
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
import { computed, watch, ref } from "vue";
import { mdiOpenInNew, mdiPail } from "@mdi/js";
import { estimatedBytesPerSec, getBucketStatus, getReadableSize, getReadableTime } from "../scripts/common";
import { getBuckets, getEC2Credentials } from "../scripts/openstack";
import { S3Client, ListBucketsCommand } from "@aws-sdk/client-s3";
import { NEW_VERSION_DATE } from "../scripts/config";

const { project, scopedToken, s3address } = defineProps(["project", "scopedToken", "s3address"]);

const emit = defineEmits(["select-buckets", "go-back"]);

watch(
  () => scopedToken,
  async (newToken) => {
    if (newToken) {
      loading.value = true;
      console.log(`Using scoped token: ${newToken}`);
      const ret = await getBuckets(newToken);
      buckets.value = ret;
      try {
        const ec2 = await getEC2Credentials(newToken, project.id);
        const client = new S3Client({
          region: "us-east-1",
          endpoint: s3address,
          credentials: {
            accessKeyId: ec2.access,
            secretAccessKey: ec2.secret,
          },
        });
        const resp = await client.send(new ListBucketsCommand());
        const s3Buckets = resp?.Buckets || [];
        // Create a bucket map to find new-version buckets
        s3BucketMap.value = new Map(s3Buckets.map((bucket) => [bucket.Name, bucket.CreationDate]));
      } catch (e) {
        console.error("Failed to retrieve s3 buckets", e);
      }
      loading.value = false;
      if (selected.value.length) {
        selected.value = [];
        // Remount table so that select event detail doesn't contain stale selection
        tableKey.value++;
      }
    }
  },
);

function selectBuckets() {
  if (!selected.value.length) {
    addToast("error", "Please select buckets to convert");
    return;
  }
  emit("select-buckets", selected.value);
}

function emitBack() {
  emit("go-back");
}

function addToast(type, msg) {
  const toast = {
    type: type,
    message: msg,
  };
  document.getElementById("select-bucket-toasts").addToast(toast);
}

/** TABLE */
const buckets = ref([]);
const s3BucketMap = ref();
const selected = ref([]);
const tableKey = ref(0);
const loading = ref(false);

const headers = [
  { key: "name", align: "center", value: "Name", sortable: false },
  { key: "status", value: "Conversion need", sortable: false },
];

const tableData = computed(() => {
  return buckets.value
    .filter((bucket) => !bucket.name.match("_segments"))
    .map((bucket) => {
      // enrich data with conversion needed status that will be passed on
      const num = getRecommendedAction(bucket);
      bucket.conversionNeed = num;
      const createdDate = s3BucketMap.value?.get(bucket.name);
      if (createdDate) {
        bucket.created = Date.parse(createdDate);
      }
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
        // keep bucket object in table data to simplify selection addition/removal
        // add segments size to bucket
        bucket: {
          value:
            bucket.count && bucket.bytes === 0 ? { ...bucket, segmentsBytes: getSegmentsBytes(bucket.name) } : bucket,
        },
      };
    });
});

const quotaNeeded = computed(() => {
  return selected.value.reduce((quota, bucket) => {
    if (bucket.count && bucket.bytes === 0) {
      const bytes = getSegmentsBytes(bucket.name);
      return quota + bytes;
    } else {
      return quota + bucket.bytes;
    }
  }, 0);
});

function getSegmentsBytes(bucketName) {
  // get bytes from segments bucket
  const segments = buckets.value.find((b) => b.name === `${bucketName}_segments`);
  return segments?.bytes ?? 0;
}

const estimatedTime = computed(() => {
  return Math.round(quotaNeeded.value / estimatedBytesPerSec);
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
    return 2;
  }

  // If the bucket doesn't have any bytes, but has content, it has likely
  // been filled with swift large objects
  if (!bucket.bytes && bucket.count) {
    return 1;
  }

  // If the bucket has a matching segemnts bucket with content, it likely
  // contains swift large objects
  if (buckets.value.find((nb) => nb.name == `${bucket.name}_segments`)?.count > 0) {
    return 1;
  }

  // If the bucket name is too long, it will likely have to be truncated
  if (bucket.name.length < 3 || bucket.name.length > 63) {
    return 1;
  }

  // If the bucket doesn't start with lowercase alphanumeric, it should
  // probably be migrated
  if (!isLowerCaseOrNum(bucket.name[0]) || !isLowerCaseOrNum(bucket.name[bucket.name.length - 1])) {
    return 1;
  }

  // If the bucket contains non-alphanumeric characters, it should probably
  // be migrated with a conforming name
  if (!bucket.name.match(/^[a-z0-9-]+$/g)) {
    return 1;
  }

  // No need to migrate buckets created with V3
  if (bucket?.created > NEW_VERSION_DATE) {
    return 0;
  }
  // Undetermined, migrate in case of sharing
  return 1;
}
</script>
<style scoped>
c-row {
  margin-top: 2rem;
}
.alert-wrapper {
  margin: 1rem 0;
}
</style>
