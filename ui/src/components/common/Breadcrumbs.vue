<!-- eslint-disable vue/multi-word-component-names -->
<script setup lang="ts">
import { computed } from 'vue'
import { LAYOUT, TYPOGRAPHY } from '@/constants/theme'
import { useDisplay, useRtl } from 'vuetify'

interface BreadcrumbItem {
  title: string
  to?: string
  disabled?: boolean
}

const props = defineProps<{
  items: BreadcrumbItem[]
}>()

const { mobile } = useDisplay()
const { isRtl } = useRtl()

function truncateToWords(title: string, wordCount: number) {
  const words = title.trim().split(/\s+/)
  return words.length > wordCount ? `${words.slice(0, wordCount).join(' ')}…` : title
}

const displayItems = computed(() =>
  props.items.map((item, index) => ({
    ...item,
    title:
      mobile.value && index === props.items.length - 1 ? truncateToWords(item.title, 2) : item.title
  }))
)
</script>

<template>
  <div class="breadcrumbs-wrapper">
    <v-breadcrumbs
      :items="displayItems"
      class="breadcrumbs-nav"
      :class="{ 'breadcrumbs-nav--small': mobile }"
      density="compact"
    >
      <template v-slot:divider>
        <v-icon :icon="isRtl ? 'mdi-chevron-left' : 'mdi-chevron-right'" size="small" />
      </template>
    </v-breadcrumbs>
  </div>
</template>

<style scoped>
.breadcrumbs-wrapper {
  /* Lets the breadcrumbs shrink instead of pushing the language filter
     control out of the flex row when the current item's title is long */
  flex: 1 1 auto;
  min-width: 0;
}

.breadcrumbs-nav {
  /* Fixed row height so the bar is the same thickness whether or not
     divider icons are rendered (icons are taller than the caption text) */
  height: 35px;
  min-width: 0;
  padding: 0 calc(v-bind(LAYOUT.VIEW_PADDING_HORIZONTAL) - 4px);
}

/* Every item (including links like Home or a translated section label,
   which can run long in some locales) ellipsizes instead of overflowing
   if it ends up squeezed for space. */
.breadcrumbs-nav :deep(.v-breadcrumbs-item) {
  min-width: 0;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.CAPTION_SIZE);
  font-weight: v-bind(TYPOGRAPHY.CAPTION_WEIGHT);
}

/* The current (non-link) item is always the last one and is the only one
   that can grow arbitrarily long (book title, author name, …), so it's the
   one given priority to claim any extra space in the row. */
.breadcrumbs-nav :deep(.v-breadcrumbs-item--disabled) {
  flex: 1 1 auto;
  font-weight: v-bind(TYPOGRAPHY.BODY_WEIGHT);
  opacity: 1;
}

.breadcrumbs-nav :deep(.v-breadcrumbs-divider) {
  flex: 0 0 auto;
  padding: 0;
}

.breadcrumbs-nav--small {
  width: 100%;
  padding: 0 calc(v-bind(LAYOUT.VIEW_PADDING_HORIZONTAL_MOBILE) - 4px);
}
</style>
