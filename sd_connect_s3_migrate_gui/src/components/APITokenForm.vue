<template>
  <h1>Retrieve an SD Connect API token</h1>

  <ol>
    <li>
      Open the
      <a href="https://sd-connect.sdqa.csc.fi/" target="_blank">SD Connect UI</a>
      and log in with user {{ user }}
    </li>
    <li>Select the matching project, {{ project.name }}, from the project selection menu</li>
    <li>
      Paste the token into the underlying field, and click continue

      <c-text-field v-model="api_token" label="Paste the SD Connect API token here"></c-text-field>

      <c-button @click="emitToken">Add token</c-button>
    </li>
  </ol>
</template>

<script setup>
const { user, project } = defineProps(["user", "project"]);

const emit = defineEmits(["gotToken"]);

let api_token = "";

function emitToken() {
  emit("gotToken", api_token);
}
</script>
