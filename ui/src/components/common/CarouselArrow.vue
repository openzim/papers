<script setup lang="ts">
import { computed } from 'vue'
import { CAROUSEL_ARROW_SIZES } from '@/constants/theme'
import { useRtl } from 'vuetify'

const props = defineProps<{
  direction: 'prev' | 'next'
  disabled?: boolean
  ariaLabel: string
  beigeShadow?: boolean
}>()

defineEmits<{
  click: []
}>()

const { isRtl } = useRtl()

const icon = computed(() => {
  const isBack = props.direction === 'prev'
  if (isBack) {
    return isRtl.value ? 'mdi-chevron-right' : 'mdi-chevron-left'
  }
  return isRtl.value ? 'mdi-chevron-left' : 'mdi-chevron-right'
})
</script>

<template>
  <button
    type="button"
    class="carousel-arrow"
    :disabled="disabled"
    :aria-label="ariaLabel"
    @click="$emit('click')"
  >
    <v-icon :icon="icon" class="arrow-icon" />
  </button>
</template>

<style scoped>
.carousel-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: v-bind(CAROUSEL_ARROW_SIZES.BUTTON + 'px');
  height: v-bind(CAROUSEL_ARROW_SIZES.BUTTON + 'px');
  border-radius: 50%;
  border: 1px solid rgb(var(--v-theme-grid));
  background: rgb(var(--v-theme-background));
  color: rgb(var(--v-theme-text));
  cursor: pointer;
  flex-shrink: 0;
  box-shadow:
    0 0 6px rgba(var(--v-theme-text), 0.1),
    0 0 12px rgba(var(--v-theme-text), 0.06);
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease;
}

.carousel-arrow:hover:not(:disabled) {
  transform: scale(1.15);
  box-shadow:
    0 0 12px rgba(var(--v-theme-text), 0.2),
    0 0 24px rgba(var(--v-theme-text), 0.12),
    0 0 36px rgba(var(--v-theme-text), 0.06);
}

.carousel-arrow:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  box-shadow: none;
}
</style>
