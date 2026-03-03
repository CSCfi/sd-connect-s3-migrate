<template>
  <div>
    <h1>Select project</h1>
    <p>SD Connect Conversion tool allows you to convert buckets from one project at a time.</p>
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
    <c-button @click="selectProject">Continue</c-button>
  </div>
</template>

<script setup>
import { ref } from "vue";
const selectedProject = ref();
const showError = ref(false);

const { projects } = defineProps(["projects"]);

const emit = defineEmits(["selectProject"]);

function selectProject() {
  if (!selectedProject.value?.value) {
    showError.value = true;
    return;
  }
  // Selected project is wrapped { value: project }
  emit("selectProject", selectedProject.value.value);
}
</script>
<style scoped>
c-select {
  width: 60%;
  padding-top: 1rem;
}
c-button {
  float: right;
}
</style>
