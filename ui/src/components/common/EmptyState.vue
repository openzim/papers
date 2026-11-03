<script setup lang="ts">
defineProps<{
  message: string
  type?: 'info' | 'warning' | 'error' | 'success'
}>()
</script>

<template>
  <v-alert class="empty-state" :type="type || 'info'" variant="tonal">
    {{ message }}
  </v-alert>
</template>

<style scoped>
.empty-state {
  margin-bottom: 2rem;
}
</style>
