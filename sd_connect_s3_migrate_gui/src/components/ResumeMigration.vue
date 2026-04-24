<template>
  <div>
    <p>
      <b>Project:</b>
      {{ project?.name }}
    </p>
    <h1>Data conversion was interrupted</h1>
    <p>
      Data conversion was interrupted due to an expired or invalid API key. Please continue conversion by creating a new
      API key via SD Connect user interface. Navigate to Support -> Create API keys.
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
    <div>
      <p>
        <b>Estimated conversion time:</b>
        {{ getTimeEstimate(0) }}
      </p>
    </div>
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
        <c-button @click="emitToken" @keyup.enter="emitToken">Continue conversion</c-button>
      </c-row>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { getTimeEstimate } from "../scripts/common";
import { mdiOpenInNew } from "@mdi/js";
import MigrationBucketTable from "./MigrationBucketTable.vue";

const { buckets, project } = defineProps(["buckets", "project"]);
const emit = defineEmits(["got-token", "cancel-migration"]);

const apiToken = ref("");
const showError = ref(false);
const clickedCancel = ref(false);

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
