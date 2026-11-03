<script setup lang="ts">
defineProps<{
  message: string
  type?: 'info' | 'warning' | 'error' | 'success'
}>()
</script>

<template>
  <v-alert class="empty-state" :type="type || 'info'" variant="tonal" rounded="lg">
    <span class="empty-state__message">{{ message }}</span>
  </v-alert>
</template>

<style scoped>
.empty-state {
  margin-bottom: 2rem;
}

.empty-state__message {
  color: rgb(var(--v-theme-text));
}
</style>
