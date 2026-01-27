<template>
  <c-login-card background-position="50% 0%" src="/img/bg.png">
  <c-login-card-title>Login to SD Connect migration tool</c-login-card-title>

  <c-login-card-content>
    <div>
      SD Connect migration tool allows you to easily convert your files uploaded via the old API
      to a format compatible with the new one. You will need to first log in using your CSC user
      account.
    </div>

    <c-text-field label="Username" hint="CSC Account username" v-model="username" />

    <c-text-field
    hint="Use your CSC user account password"
    label="Password"
    type="password"
    v-model="password"
    />
  </c-login-card-content>

  <c-login-card-actions justify="space-between">
    <c-button size="large" @click="allasLogin().then(() => {}).catch(e => {console.log(e)})">Submit</c-button>
  </c-login-card-actions>

  <c-link href="http://csc.fi" underline>Forgot password?</c-link>
  </c-login-card>
</template>

<script setup>
import { loginWithUserpass } from '../scripts/openstack';


let username = "";
let password = "";

let unscoped = "";

const emit = defineEmits([
  "loginSuccessful",
  "loginFailed",
]);

async function allasLogin() {
  unscoped = await loginWithUserpass(username, password);

  if (unscoped) {
    emit("loginSuccessful", unscoped, username);
  } else [
    emit("loginFailed")
  ]
}

</script>
