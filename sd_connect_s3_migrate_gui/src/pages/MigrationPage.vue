<template>
  <div id="main">
    <c-toolbar class="relative">
      <c-csc-logo />
      SD Connect Conversion tool
    </c-toolbar>
    <div id="separator"></div>
    <!-- Main contents for the application -->
    <div id="login-card" v-if="step == 0">
      <Login @login-successful="handleProjectDiscovery" />
    </div>

    <div id="steps-wrapper" v-else>
      <c-steps v-model="step">
        <c-step>Select project</c-step>
        <c-step>Add API key</c-step>
        <c-step>Select buckets</c-step>
        <c-step>Data conversion</c-step>
        <c-step>Conversion complete</c-step>
      </c-steps>

      <div id="select-card" v-show="step == 1">
        <Select @select-project="selectProjectAndScopeToken" :projects="projects" ref="projectSelect" />
      </div>

      <div id="token-card" v-show="step == 2">
        <Token @got-token="handleAddAPIToken" @go-back="goBack" :project="activeProject" ref="tokenInput" />
      </div>

      <div id="buckets-card" v-show="step == 3">
        <SelectBuckets
          @select-buckets="handleSelectBuckets"
          @go-back="goBack"
          :project="activeProject"
          :scopedToken="scopedToken"
        />
      </div>

      <div id="migration-card" v-if="step == 4">
        <Migration
          @buckets-migrated="handleBucketsMigrated"
          :buckets="selectedBuckets"
          :scopedToken="scopedToken"
          :project="activeProject"
          :s3address="getS3endpoint()"
        />
      </div>

      <div id="results-card" v-if="step == 5">
        <Results
          :project="activeProject"
          :migratedBuckets="migratedBuckets"
          @start-new-conversion="startNewConversion"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, useTemplateRef } from "vue";

// Component imports
import Login from "../components/LoginForm.vue";
import Token from "../components/APITokenForm.vue";
import Select from "../components/ProjectSelection.vue";
import SelectBuckets from "../components/SelectBuckets.vue";
import Migration from "../components/BucketMigration.vue";
import Results from "../components/MigrationResults.vue";
import { discoverTokenProjects, getS3endpoint, getScopedToken } from "../scripts/openstack";

const step = ref(0);
const selectRef = useTemplateRef("projectSelect");
const tokenRef = useTemplateRef("tokenInput");

// Data gained from login
let user = "";
let unscopedToken = "";
const projects = ref([]);

// Data gained from step 1
const activeProject = ref(null);
const scopedToken = ref("");

// Data gained from step 2
const apiToken = ref("");

// Data gained from step 3
const selectedBuckets = ref([]);

// Data gained from step 4
const migratedBuckets = ref([]);

// Handle the project discovery from unscoped token
async function handleProjectDiscovery(unscoped, username) {
  unscopedToken = unscoped;
  user = username;
  projects.value = await discoverTokenProjects(unscoped);

  console.log(user);
  console.log(unscopedToken);

  step.value += 1;
}

// Handle project selection
async function selectProjectAndScopeToken(project) {
  if (activeProject.value?.id !== project.id) {
    activeProject.value = project;
    scopedToken.value = await getScopedToken(unscopedToken, project.id);
    console.log(scopedToken.value);
  }
  step.value += 1;
}

// Handle API token addition
async function handleAddAPIToken(token) {
  apiToken.value = token;
  console.log(apiToken.value);

  step.value += 1;
}

// Handle migrate bucket selection
async function handleSelectBuckets(buckets) {
  console.log(buckets);
  selectedBuckets.value = buckets;

  step.value += 1;
}

// Handle migrated buckets
async function handleBucketsMigrated(buckets) {
  migratedBuckets.value = buckets;
  console.log(migratedBuckets.value);

  step.value += 1;
}

function goBack() {
  step.value--;
}

function startNewConversion() {
  step.value = 1;
  // reset values
  activeProject.value = null;
  selectRef.value.reset();
  apiToken.value = "";
  tokenRef.value.reset();
  scopedToken.value = "";
  selectedBuckets.value = [];
  migratedBuckets.value = [];
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
  position: relative;
  height: 8px;
  width: 100%;
  background-color: var(--c-primary-200);
}

c-steps {
  padding-bottom: 3rem;
}
</style>
