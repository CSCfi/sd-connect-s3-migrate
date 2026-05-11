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
      <c-alert type="error">Error deleting original incompatible buckets.</c-alert>
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
import { getReadableSize, timeout } from "../scripts/common";

const { project, migratedBuckets } = defineProps(["project", "migratedBuckets"]);
const emit = defineEmits(["start-new-conversion"]);

const alert = ref("match");
const deleteSuccess = ref();
const deleting = ref(false);

async function onDelete() {
  if (deleting.value) return;
  try {
    deleting.value = true;
    for (const bucket of migratedBuckets) {
      // TODO delete
      // simulate deletion for now
      await timeout(200);
      console.log(bucket);
    }
    deleteSuccess.value = true;
  } catch {
    deleteSuccess.value = false;
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
