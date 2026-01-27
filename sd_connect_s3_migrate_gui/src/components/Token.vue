<template>
  <h1>Retrieve an SD Connect API token</h1>

  <ol>
    <li>Open the <a href="https://sd-connect.sdqa.csc.fi/" target="_blank">SD Connect UI</a> and log in with user {{ user }}</li>
    <li>Select the matching project, {{ project.name }}, from the project selection menu</li>
    <li>
      Open the tokens view by navigating to "Support" -> "Create API tokens"

      <section>
        <img src="/src/static/support_menu.png"></img>
      </section>
      <section>
        <img src="/src/static/api_tokens.png"></img>
      </section>
    </li>
    <li>
      Fill in a name for the token (need not match the suggestion in the picture) and click "Create token"

      <section>
        <img src="/src/static/create_modal.png"></img>
      </section>
    </li>
    <li>
      Click "Copy token", you should see the following toast marking the token is successfully copied

      <section>
        <img src="/src/static/temp_token_copy.png"></img>
      </section>
      <section>
        <img src="/src/static/copy_toast.png"></img>
      </section>
    </li>
    <li>
      Paste the token into the underlying field, and click continue

      <c-text-field v-model="api_token" label="Paste the SD Connect API token here"></c-text-field>

      <c-button @click="emitToken">Add token</c-button>
    </li>
  </ol>
</template>

<script setup>

const {
  user,
  project,
} = defineProps([
  "user",
  "project",
]);

const emit = defineEmits([
  "gotToken",
]);

let api_token = "";

function emitToken() {
  emit("gotToken", api_token);
}

</script>
