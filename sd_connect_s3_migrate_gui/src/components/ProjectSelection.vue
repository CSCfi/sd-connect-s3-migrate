<template>
  <div>
    <h1>Select project</h1>
    <p>SD Connect Conversion tool allows you to convert buckets from one project at a time.</p>
    <c-alert type="warning">
      <b>If your project has more than 1 TB of data</b>
      If your project has more than 1 TB of data, contact servicedesk@csc.fi with the subject "Sensitive data". We will
      plan the conversion process together with you.
    </c-alert>
    <c-select
      v-model="selectedProject"
      v-control
      label="Select project"
      placeholder="Select project..."
      option-as-selection
      return-object
      :valid="!showError"
      @changeValue="showError = false"
    >
      <c-option v-for="project in projects" :value="project" :key="project.name">{{ project.name }}</c-option>
    </c-select>
    <c-button @click="selectProject" @keyup.enter="selectProject">Continue</c-button>
  </div>
</template>

<script setup>
import { ref } from "vue";
const selectedProject = ref(null);
const showError = ref(false);

const { projects } = defineProps(["projects"]);

const emit = defineEmits(["select-project"]);

// expose method to parent
defineExpose({ reset });

function selectProject() {
  if (!selectedProject.value?.value) {
    showError.value = true;
    return;
  }
  // Selected project is wrapped { value: project }
  emit("select-project", selectedProject.value.value);
}

function reset() {
  selectedProject.value = null;
}
</script>
<style scoped>
h1 {
  margin-top: 3rem;
}

c-select {
  width: 60%;
  padding-top: 1rem;
}
c-button {
  margin-top: 1.5rem;
  float: right;
}
</style>
