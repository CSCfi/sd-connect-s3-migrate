<template>
  <div>
    <p>
      <b>Project:</b>
      {{ project?.name }} {{ project?.description }}
    </p>
    <h1>Add temporary API key</h1>
    <p>Create your API key via SD Connect user interface. Navigate to Support -> Create API key.</p>
    <!--TODO add link when it exists-->
    <c-link underline href="#" target="_blank">
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
      <c-button outlined @click="goBack" @keyup.enter="goBack">Cancel</c-button>
      <c-button @click="emitToken" @keyup.enter="emitToken">Continue</c-button>
    </c-row>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { mdiOpenInNew } from "@mdi/js";

const { project } = defineProps(["project"]);

const emit = defineEmits(["gotToken", "goBack"]);

const apiToken = ref();
const showError = ref(false);

function emitToken() {
  if (!apiToken.value) {
    showError.value = true;
    return;
  }
  emit("gotToken", apiToken.value);
}

function goBack() {
  showError.value = false;
  emit("goBack");
}
</script>

<style scoped>
/* wrap unwieldy c-text-field to style it */
.text-wrapper {
  width: 60%;
  margin: 1.5rem 0;
}
</style>
