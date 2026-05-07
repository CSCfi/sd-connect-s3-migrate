<template>
  <div>
    <p>
      <b>Project:</b>
      {{ project?.name }}
    </p>
    <h1>Data conversion was interrupted</h1>
    <div v-if="reason === interruptReasons.quitApp">
      <p>
        Data conversion was interrupted due to the conversion tool getting closed. Please continue the conversion by
        clicking the button below.
      </p>
    </div>
    <div v-else-if="reason === interruptReasons.apiKeyError">
      <p>
        Data conversion was interrupted due to an expired or invalid API key. Please continue the conversion by creating
        a new API key via SD Connect user interface. Navigate to Support -> Create API keys.
      </p>
      <c-link
        underline
        href="https://docs.csc.fi/data/sensitive-data/sd-connect-conversion-tool-ui/#33-add-projects-temporary-api-key"
        target="_blank"
      >
        See detailed instructions
        <c-icon :path="mdiOpenInNew" />
      </c-link>
      <div class="text-wrapper">
        <c-text-field
          v-model="apiToken"
          label="API key"
          :valid="!showError"
          @changeValue="showError = false"
        ></c-text-field>
      </div>
    </div>
    <div v-else>
      <p>
        Data conversion was interrupted due to an unexptected error. Please continue the conversion by clicking the
        button below.
      </p>
    </div>
    <div>
      <p>
        <b>Estimated conversion time:</b>
        {{ getTimeEstimate(estimatedTime) }}
      </p>
      <MigrationBucketTable :buckets="buckets" />
      <div class="action-wrapper">
        <c-alert v-if="clickedCancel" type="warning">
          <c-row justify="space-between">
            Are you sure you want to cancel the conversion? This action cannot be undone.
            <div class="alert-actions">
              <c-button outlined @click="cancel" @keyup.enter="cancel">Yes</c-button>
              <c-button @click="clickedCancel = false" @keyup.enter="clickedCancel = false">No</c-button>
            </div>
          </c-row>
        </c-alert>
        <c-row justify="space-between" class="step-actions">
          <c-button outlined @click="clickedCancel = true" @keyup.enter="clickedCancel = true">
            Cancel conversion
          </c-button>
          <c-button @click="handleContinue" @keyup.enter="handleContinue">Continue conversion</c-button>
        </c-row>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { estimatedBytesPerSec, getTimeEstimate, interruptReasons } from "../scripts/common";
import { mdiOpenInNew } from "@mdi/js";
import MigrationBucketTable from "./MigrationBucketTable.vue";

const { buckets, project, reason } = defineProps(["buckets", "project", "reason"]);
const emit = defineEmits(["got-token", "cancel-migration", "continue-migration"]);

const apiToken = ref("");
const showError = ref(false);
const clickedCancel = ref(false);
const bytesLeft = ref(0);

onMounted(() => {
  // Buckets from loaded migration state
  // Or selectedBuckets when api key error occurs before saving migration state
  for (const bucket of buckets) {
    // Non-migrated segmented objects will have size 0
    // Subtract migrated bytes
    let bucketBytesLeft = bucket.bytes;
    if (bucket?.objects) {
      for (const object of bucket.objects) {
        if (object.contentDone) {
          bucketBytesLeft -= object.bytes;
        }
      }
    }
    bytesLeft.value += bucketBytesLeft;
  }
});

const estimatedTime = computed(() => {
  return Math.ceil(bytesLeft.value / estimatedBytesPerSec);
});

function handleContinue() {
  if (reason === interruptReasons.apiKeyError) emitToken();
  else emit("continue-migration");
}

function emitToken() {
  if (!apiToken.value) {
    showError.value = true;
    return;
  }
  emit("got-token", apiToken.value);
}

function cancel() {
  clickedCancel.value = false;
  emit("cancel-migration");
}
</script>
<style scoped>
.text-wrapper,
.action-wrapper,
.step-actions {
  margin-top: 2rem;
}
.alert-actions > * {
  margin-right: 1rem;
}
.text-wrapper {
  width: 60%;
}
</style>
