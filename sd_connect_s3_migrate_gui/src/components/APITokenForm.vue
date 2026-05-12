<template>
  <div>
    <p>
      <b>Project:</b>
      {{ project?.name }}
    </p>
    <h1>Add temporary API key</h1>
    <p>
      Create your API key via
      <c-link underline :href="sdConnectLink" target="_blank">
        SD Connect
        <c-icon :path="mdiOpenInNew" />
      </c-link>
    </p>
    <ol>
      <li>Login and select the project you are converting.</li>
      <li>Navigate to Support in the top bar and select Create API keys.</li>
      <li>After creating the key, copy it and paste it to the field below.</li>
    </ol>
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
    <c-row justify="space-between">
      <c-button outlined @click="goBack" @keyup.enter="goBack">Back</c-button>
      <c-button @click="emitToken" @keyup.enter="emitToken">Continue</c-button>
    </c-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { mdiOpenInNew } from "@mdi/js";
import { getSDConnectAPIEndpoint } from "../scripts/config";

const { project } = defineProps(["project"]);

const emit = defineEmits(["got-token", "go-back"]);

defineExpose({ reset });

const sdConnectLink = ref("");

onMounted(async () => {
  sdConnectLink.value = await getSDConnectAPIEndpoint();
});

const apiToken = ref("");
const showError = ref(false);

function emitToken() {
  if (!apiToken.value) {
    showError.value = true;
    return;
  }
  emit("got-token", apiToken.value);
}

function goBack() {
  showError.value = false;
  emit("go-back");
}

function reset() {
  apiToken.value = "";
}
</script>

<style scoped>
/* wrap unwieldy c-text-field to style it */
.text-wrapper {
  width: 60%;
  margin: 1.5rem 0;
}
</style>
