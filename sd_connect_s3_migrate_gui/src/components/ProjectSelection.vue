<template>
  <h1>Select the project to use:</h1>

  <ul>
    <li v-for="project in projects" :key="project.name">
      {{ project.name }}
      <c-button @click="selectProject(project)">Select project</c-button>
    </li>
  </ul>
</template>

<script setup>
const { projects } = defineProps(["projects"]);

const emit = defineEmits(["selectProject"]);

function selectProject(project) {
  emit("selectProject", project);
}
</script>
