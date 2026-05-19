<template>
  <div id="main">
    <c-toolbar class="relative">
      <c-csc-logo />
      SD Connect Conversion tool
    </c-toolbar>
    <div id="separator"></div>
    <!-- Main contents for the application -->
    <div id="login-card" v-if="step == 0">
      <Login v-model:user="user" :user-exists="userExists" @login-successful="handleProjectDiscovery" />
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
          :s3address="getS3endpoint()"
        />
      </div>

      <div id="migration-card" v-if="step == 4">
        <Migration
          v-if="!migrationInterruptReason"
          @buckets-migrated="handleBucketsMigrated"
          @error="handleMigrationError"
          @update-migration-state="saveMigrationState"
          :sdApiToken="apiToken"
          :buckets="selectedBuckets"
          :oldMigrateBuckets="oldMigrateBuckets"
          :scopedToken="scopedToken"
          :project="activeProject"
          :s3address="getS3endpoint()"
        />
        <ResumeMigration
          v-else
          @got-token="handleReaddAPIToken"
          @cancel-migration="handleCancelMigration"
          @continue-migration="handleContinueMigration"
          :reason="migrationInterruptReason"
          :project="activeProject"
          :buckets="oldMigrateBuckets.length ? oldMigrateBuckets : selectedBuckets"
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
import { computed, ref, useTemplateRef, toRaw, onMounted, watch } from "vue";

// Component imports
import Login from "../components/LoginForm.vue";
import Token from "../components/APITokenForm.vue";
import Select from "../components/ProjectSelection.vue";
import SelectBuckets from "../components/SelectBuckets.vue";
import Migration from "../components/BucketMigration.vue";
import ResumeMigration from "../components/ResumeMigration.vue";
import Results from "../components/MigrationResults.vue";
import { discoverTokenProjects, getS3endpoint, getScopedToken } from "../scripts/openstack";
import { interruptReasons } from "../scripts/common";

// Type imports
/**
 * @typedef {import { OpenstackProject } from "../scripts/types.js"}
 */
/**
 * @typedef {import { OpenstackBucket } from "../scripts/types.js"}
 */
/**
 * @typedef {import { MigrationBucketList } from "../scripts/types.js"}
 */
/**
 * @typedef {import { MigrationState } from "../scripts/types.js"}
 */

const step = ref(0);
const selectRef = useTemplateRef("projectSelect");
const tokenRef = useTemplateRef("tokenInput");
const migrationInterruptReason = ref("");

const oldMigrateBuckets = ref([]);

// Data gained from login
const user = ref("");
const unscopedToken = ref("");
const projects = ref([]);

// Data gained from step 1
const activeProject = ref({});
const scopedToken = ref("");

// let gained from step 2
const apiToken = ref("");

// Data gained from step 3
const selectedBuckets = ref([]);

// Data gained from step 4
const migratedBuckets = ref([]);

// Track whether this component updates user value
const userExists = ref(false);

onMounted(() => {
  // Attempt loading the possible previous migration state
  loadMigrationState().then(() => {
    console.log("Scheduled loading interrupted migration.");
  });
});

const preventSuspend = computed(() => {
  return step.value === 4 && migrationInterruptReason.value === "";
});

watch(preventSuspend, (newValue) => {
  if (newValue) {
    // Communicate to main channel to prevent app suspension
    console.log("Start app suspension prevention");
    window.powerSaveBlocker.start();
  } else {
    console.log("Stop app suspension prevention");
    window.powerSaveBlocker.stop();
  }
});

/**
 * Save the migration state to default location
 * @param {MigrationBucketList} buckets - the list of buckets as the current migration state
 */
async function saveMigrationState(buckets) {
  // The migration bucket list is missing part of the migration state
  console.log("Migration state save called.");

  const migrationState = {
    username: toRaw(user.value),
    apiToken: toRaw(apiToken.value),
    timestamp: Math.floor(Date.now() / 1000),
    project: toRaw(activeProject.value),
    buckets: buckets,
  };

  console.log("Saving migration state:");
  console.log(migrationState);
  await window.stateAPI.saveState(migrationState);

  return;
}

/**
 * Load the interrupted migration state if it exists
 * @returns { (MigrationState | null) } - The state of the interrupted migration
 */
async function loadMigrationState() {
  console.log("Loading migration state from default location.");

  const migrationState = await window.stateAPI.loadState();

  if (migrationState !== null) {
    console.log("Found interrupted migration process. Continuing migration.");
    console.log(migrationState);

    // Enter the parameters from the migration state
    user.value = migrationState.username;
    activeProject.value = migrationState.project;
    oldMigrateBuckets.value = migrationState.buckets;
    apiToken.value = migrationState.apiToken;

    migrationInterruptReason.value = interruptReasons.quitApp;
    userExists.value = true;
  }
}

/**
 * Handle the project discovery from unscoped token
 * @param {string} unscoped - unscoped token of the user logging in
 * @param {string} username - name of the user logging in
 */
async function handleProjectDiscovery(unscoped) {
  unscopedToken.value = unscoped;
  projects.value = await discoverTokenProjects(unscoped);

  if (migrationInterruptReason.value) {
    console.log(activeProject.value);
    scopedToken.value = await getScopedToken(unscopedToken.value, activeProject.value.id);
    step.value = 4;
  } else {
    step.value += 1;
  }
  console.log(user.value);
  console.log(unscopedToken.value);
}

/**
 * Handle project selection
 * @param {OpenstackProject} project - the project selected for scoping the token
 */
async function selectProjectAndScopeToken(project) {
  if (activeProject.value?.id !== project.id) {
    activeProject.value = project;
    scopedToken.value = await getScopedToken(unscopedToken.value, project.id);
    console.log(scopedToken.value);
  }

  step.value += 1;
}

/**
 * Handle API token addition
 * @param {string} token - SD Connect API token to be added
 */
async function handleAddAPIToken(token) {
  apiToken.value = token;
  console.log(apiToken.value);

  step.value += 1;
}

/**
 * Handle migrate bucket selection
 * @param {OpenstackBucket[]} buckets - buckets that are to be migrated
 */
async function handleSelectBuckets(buckets) {
  console.log(buckets);
  selectedBuckets.value = buckets;

  step.value += 1;
}

/**
 * Handle migrated buckets
 * @param {MigrationBucketList} buckets - buckets that were migrated
 */
async function handleBucketsMigrated(buckets) {
  migratedBuckets.value = buckets;
  console.log(migratedBuckets.value);

  // Clear the migration state
  await saveMigrationState(toRaw(buckets));
  await window.stateAPI.finishState();

  step.value += 1;
}

/**
 * Navigate back to the previous step
 */
function goBack() {
  step.value--;
}

/**
 * Reset conversion UI state tracking values to start
 */
function startNewConversion() {
  step.value = 1;
  // reset values
  activeProject.value = null;
  selectRef.value.reset();
  apiToken.value = "";
  tokenRef.value.reset();
  scopedToken.value = "";
  selectedBuckets.value = [];
  oldMigrateBuckets.value = [];
  migratedBuckets.value = [];
  migrationInterruptReason.value = "";
}

async function handleMigrationError(error) {
  migrationInterruptReason.value = error;

  // Get buckets from migration state
  const migrationState = await window.stateAPI.loadState();
  if (migrationState !== null) {
    oldMigrateBuckets.value = migrationState.buckets;
  }

  step.value = 4;
}

function handleReaddAPIToken(token) {
  apiToken.value = token;
  handleContinueMigration();
}

function handleContinueMigration() {
  migrationInterruptReason.value = "";
}

async function handleCancelMigration() {
  console.log("Migration cancelled");
  await window.stateAPI.clearState();
  startNewConversion();
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
