<template>
  <div id="main">
    <c-toolbar>
      <c-csc-logo />
      SD Connect Conversion tool
    </c-toolbar>
    <div id="separator"></div>
    <!-- Main contents for the application -->
    <div id="login-card" v-if="step == 0">
      <Login @loginSuccessful="handleProjectDiscovery" />
    </div>

    <div id="steps-wrapper" v-else>
      <c-steps v-model="step">
        <c-step>Select project</c-step>

        <c-step>Add API key</c-step>

        <c-step>{{ buckets.length > 0 ? `Selected buckets: ${buckets.length}` : "Select buckets" }}</c-step>

        <c-step>Data conversion</c-step>

        <c-step>Conversion complete</c-step>
      </c-steps>

      <div id="select-card" v-show="step == 1">
        <Select @selectProject="selectProjectAndScopeToken" :projects="projects" />
      </div>

      <div id="token-card" v-show="step == 2">
        <Token @gotToken="handleAddAPIToken" @goBack="goBack" :project="active_project" />
      </div>

      <div id="buckets-card" v-if="step == 3">
        <Buckets @selectBuckets="handleSelectBuckets" :scopedToken="scopedToken" />
      </div>

      <div id="migration-card" v-if="step == 4">
        <Migration
          @bucketsMigrated="handleBucketsMigrated"
          :buckets="buckets"
          :scopedToken="scopedToken"
          :activeProject="active_project"
          :s3address="getS3endpoint()"
        />
      </div>

      <div id="results-card" v-if="step == 5">
        <Results :migratedBuckets="migratedBuckets" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

// Component imports
import Login from "../components/LoginForm.vue";
import Token from "../components/APITokenForm.vue";
import Select from "../components/ProjectSelection.vue";
import Buckets from "../components/BucketTable.vue";
import Migration from "../components/BucketMigration.vue";
import Results from "../components/MigrationResults.vue";
import { discoverTokenProjects, getS3endpoint, getScopedToken } from "../scripts/openstack";

const step = ref(0);

// Data gained from login
let user = "";
let unscopedToken = "";
let projects = [];

// Data gained from step 1
let active_project;
let scopedToken = "";

// Data gained from step 2
let api_token = "";

// Data gained from step 3
let buckets = [];

// Data gained from step 4
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
  active_project = project;

  scopedToken = await getScopedToken(unscopedToken, active_project.id);
  console.log(scopedToken);

  step.value += 1;
}

// Handle API token addition
async function handleAddAPIToken(token) {
  api_token = token;
  console.log(api_token);

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

function goBack() {
  step.value--;
}
</script>

<style lang="css" scoped>
#login-card,
#steps-wrapper {
  width: 50%;
  margin: auto;
  padding: 5rem 0;
}

#steps-wrapper {
  width: 90%;
}

#separator {
  position: fixed;
  height: 8px;
  width: 100%;
  background-color: var(--c-primary-200);
}

c-steps {
  padding-bottom: 3rem;
}
</style>
