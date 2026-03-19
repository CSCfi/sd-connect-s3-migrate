<template>
  <div class="step-content">
    <p>
      <b>Project:</b>
      {{ project?.name }} {{ project?.description }}
    </p>
    <h1>Data conversion is complete</h1>
    <div v-if="showDeleteAlert">
      <c-alert type="error">
        <c-row gap="100" justify="space-between" align="center">
          <span class="alert-text">
            Your buckets have been copied and converted to be compatible with SD Connect v3.
            <br />
            <br />
            Would you like to delete the original incompatible buckets now?
          </span>
          <div class="actions">
            <c-button outlined @click="showDeleteAlert = false">Keep</c-button>
            <c-button @click="onDelete" :loading="deleting">Delete</c-button>
          </div>
        </c-row>
      </c-alert>
      <MigrationBucketTable :buckets="migratedBuckets" />
    </div>
    <div v-if="deleteSuccess === true">
      <c-alert type="success">Original incompatible buckets were deleted successfully.</c-alert>
    </div>
    <div v-if="deleteSuccess === false">
      <c-alert type="error">Error deleting original incompatible buckets.</c-alert>
    </div>
    <c-row v-if="!showDeleteAlert" gap="16" justify="end">
      <c-button @click="quit" outlined>Close application</c-button>
      <c-button @click="startConversion">Start new conversion</c-button>
    </c-row>
  </div>
</template>

<script setup>
import { ref } from "vue";
import MigrationBucketTable from "./MigrationBucketTable.vue";
import { timeout } from "../scripts/common";

const { project, migratedBuckets } = defineProps(["project", "migratedBuckets"]);
const emit = defineEmits(["start-new-conversion"]);

const showDeleteAlert = ref(true);
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
  showDeleteAlert.value = false;
}
function quit() {
  window.close();
}
function startConversion() {
  if (deleting.value) return;
  emit("start-new-conversion");
}
</script>
<style scoped>
.step-content > div,
.step-content > c-row {
  margin-top: 2rem;
}
.alert-text {
  flex: 1;
}
.actions > * {
  margin-right: 1rem;
}
</style>
