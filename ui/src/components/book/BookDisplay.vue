<script setup lang="ts">
import { computed } from 'vue'
import type { BookPreview } from '@/types'
import BooksGrid from '@/components/book/BooksGrid.vue'
import BooksList from '@/components/book/BooksList.vue'
import SortAndLimitControl from '@/components/common/SortAndLimitControl.vue'
import type { CatalogWindow, SortState } from '@/composables/useBooksWindow'
import { useBookDisplay } from '@/composables/useBookDisplay'
import type { BookGridVariant } from '@/constants/theme'

const props = defineProps<{
  books: BookPreview[]
  columns: number
  variant?: BookGridVariant
  type?: 'books' | 'authors' | 'shelves'
  catalog?: CatalogWindow
  sort?: SortState
}>()

const emit = defineEmits<{
  'update:displayedCount': [number]
}>()

const {
  sortBy,
  sortOrder,
  viewMode,
  isGridView,
  displayedBooks,
  displayedRange,
  catalogTotal,
  hasMoreBooks,
  sentinelRef
} = useBookDisplay(
  computed(() => props.books),
  props.catalog,
  props.sort
)

function onDisplayedCount(count: number) {
  emit('update:displayedCount', count)
}
</script>

<template>
  <div>
    <sort-and-limit-control
      v-model:sort-by="sortBy"
      v-model:sort-order="sortOrder"
      v-model:view-mode="viewMode"
      :current="displayedRange"
      :total="catalogTotal"
      :type="type || 'books'"
    />
    <books-grid v-if="isGridView" :books="displayedBooks" :columns="columns" :variant="variant" />
    <books-list v-else :books="displayedBooks" @update:displayed-count="onDisplayedCount" />

    <div v-if="hasMoreBooks" ref="sentinelRef" class="text-body-small text-center py-4">
      {{ $t('common.loading') }}
    </div>
  </div>
</template>
