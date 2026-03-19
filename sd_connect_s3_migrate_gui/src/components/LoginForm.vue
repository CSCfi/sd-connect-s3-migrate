<template>
  <div>
    <h1>Login to SD Connect Conversion tool</h1>
    <p>
      SD Connect Conversion tool allows you to easily convert your files from SD Connect 1.0 and 2.0 to be compatible
      with SD Connect 3.0.
    </p>
    <p>Login with your CSC credentials.</p>
    <form @submit.prevent="allasLogin">
      <c-text-field
        label="CSC username"
        v-model="username"
        :valid="!loginFailed"
        hide-details
        @changeValue="loginFailed = false"
        @keyup.enter="allasLogin"
      />
      <c-text-field
        label="Password"
        type="password"
        v-model="password"
        :valid="!loginFailed"
        validation="CSC username or password is incorrect"
        @changeValue="loginFailed = false"
        @keyup.enter="allasLogin"
      />
      <c-button size="large" type="submit">Log in</c-button>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { loginWithUserpass } from "../scripts/openstack";

let username = "";
let password = "";
let unscoped = "";
let loginFailed = ref(false);

const emit = defineEmits(["login-successful"]);

async function allasLogin() {
  if (!username || !password) {
    loginFailed.value = true;
    return;
  }
  unscoped = await loginWithUserpass(username, password);
  if (unscoped) {
    loginFailed.value = false;
    emit("login-successful", unscoped, username);
  } else {
    loginFailed.value = true;
  }
}
</script>

<style scoped>
form > * {
  margin-top: 1rem;
  /* Add transparent border to force c-text-field margin */
  border: 1px solid transparent;
}
</style>
