<template>
  <h2>Bucket migration results:</h2>

  <ul>
    <li>
      Total migrated buckets: {{ migratedBuckets?.length }}
    </li>
    <li>
      Total migrated objects: {{ migratedBuckets?.reduce(
        (total, bucket) => total += bucket.objects.length,
        0
      ) }}
    </li>
  </ul>
</template>

<script setup>

const {
  migratedBuckets,
} = defineProps([
  "migratedBuckets",
]);

</script>
