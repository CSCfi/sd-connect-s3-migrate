<template>

  <h1>
    SD Connect v2 -> v3 migration tool
  </h1>

  <div>

  </div>

  <c-steps v-model="step">
    <c-step>{{ user ? `Logged in as: ${user}` : `Log In` }}</c-step>
    
    <c-step>{{ active_project ? `Selected project: ${active_project.name}` : "Select project" }}</c-step>

    <c-step>{{ api_token ? "API token retrieved" : "Retrieve an API token" }}</c-step>
    
    <c-step>{{ buckets.length > 0 ? `Selected buckets: ${buckets.length}` : "Select buckets for migration" }}</c-step>

    <c-step>Migrate buckets</c-step>

    <c-step>Migration result</c-step>
  </c-steps>

  <!-- Main contents for the application -->
  <div
    id="login-card"
    v-if="step == 1"
  >
    <Login @loginSuccessful="handleProjectDiscovery" />
  </div>

  <div id="select-card" v-if="step == 2">
    <Select @selectProject="selectProjectAndScopeToken" :projects="projects" />
  </div>

  <div id="token-card" v-if="step == 3">
    <Token @gotToken="handleAddAPIToken" :project="active_project" :user="user" />
  </div>
  
  <div id="buckets-card" v-if="step == 4">
    <Buckets @selectBuckets="handleSelectBuckets" :scopedToken="scopedToken" />
  </div>

  <div id="migration-card" v-if="step == 5">
    <Migration @bucketsMigrated="handleBucketsMigrated" :buckets="buckets" :scopedToken="scopedToken" :activeProject="active_project" :s3address="getS3endpoint()" />
  </div>

  <div id="results-card" v-if="step == 6">
    <Results :migratedBuckets="migratedBuckets" />
  </div>
</template>

<script setup>
import { ref } from 'vue';

// Component imports
import Login from "../components/Login.vue";
import Token from "../components/Token.vue";
import Select from '../components/Select.vue';
import Buckets from '../components/Buckets.vue';
import Migration from '../components/Migration.vue';
import Results from '../components/Results.vue';
import { discoverTokenProjects, getS3endpoint, getScopedToken } from '../scripts/openstack';

const step = ref(1);

// Data gained from step 1
let user = "";
let unscopedToken = "";
let projects = [];

// Data gained from step 2
let active_project = "";
let scopedToken = "";

// Data gained from step 3
let api_token = "";

// Data gained from step 4
let buckets = [];

// Data gained from step 5
let migratedBuckets = {};

// Handle the project discovery from unscoped token
async function handleProjectDiscovery(unscoped, username) {
  console.log(user);
  console.log(unscoped);

  unscopedToken = unscoped;
  user = username;

  projects = await discoverTokenProjects(unscoped);

  step.value += 1;
}

// Handle project selection
async function selectProjectAndScopeToken(project) {
  console.log(project);
  active_project = project;

  scopedToken = await getScopedToken(unscopedToken, active_project.id);
  console.log(scopedToken);

  step.value += 1;
}

// Handle API token addition
async function handleAddAPIToken(token) {
  console.log(token);

  api_token = token;

  step.value += 1;
}

// Handle migrate bucket selection
async function handleSelectBuckets(migrateBuckets) {
  console.log(migrateBuckets);
  buckets = migrateBuckets;

  step.value += 1;
}

// Handle migrated buckets
async function handleBucketsMigrated(buckets) {
  migratedBuckets = buckets;
  console.log(migratedBuckets);

  step.value += 1;
}

</script>

<style lang="css">

#login-card {
  width: 60%;
  margin: auto;
  padding-top: 2rem;
  padding-bottom: 2rem;
}

</style>
