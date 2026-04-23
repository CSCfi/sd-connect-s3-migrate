<template>
  <div>
    <h1>Login to SD Connect Conversion tool</h1>
    <c-alert type="error" v-if="!!user">
      <h3>Data conversion was interrupted</h3>
      Please login to choose how to continue.
    </c-alert>
    <p>
      With the conversion tool, you can easily convert buckets from previous versions to use them with the current SD
      Connect.
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
        :disabled="!!user"
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
const { user } = defineProps(["user"]);

let username = ref(user);
let password = ref("");
let unscoped = ref("");
let loginFailed = ref(false);

const emit = defineEmits(["login-successful"]);

async function allasLogin() {
  if (!username.value || !password.value) {
    loginFailed.value = true;
    return;
  }
  unscoped.value = await loginWithUserpass(username.value, password.value);
  if (unscoped.value) {
    loginFailed.value = false;
    emit("login-successful", unscoped.value, username.value);
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
c-alert h3 {
  margin: 0;
}
</style>
