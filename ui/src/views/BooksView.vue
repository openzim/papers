<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import BackToTopButton from '@/components/common/BackToTopButton.vue'
import BookDisplay from '@/components/book/BookDisplay.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { useBooksWindow } from '@/composables/useBooksWindow'
import { LAYOUT } from '@/constants/theme'
import { MESSAGES } from '@/constants/messages'

const { t } = useI18n()

const { books, loading: booksLoading, catalog, sort, load: loadBooks } = useBooksWindow()

onMounted(() => {
  loadBooks()
})
</script>

<template>
  <div class="books-view">
    <loading-spinner v-if="booksLoading" :message="t('common.loading')" />
    <book-display
      v-else-if="books.length > 0"
      :books="books"
      :catalog="catalog"
      :sort="sort"
      :columns="5"
      type="books"
    />
    <empty-state v-else :message="t(MESSAGES.NO_BOOKS)" type="info" />
    <back-to-top-button />
  </div>
</template>

<style scoped>
.books-view {
  padding: v-bind(LAYOUT.VIEW_PADDING);
  max-width: v-bind(LAYOUT.MAX_CONTENT_WIDTH);
  margin: 0 auto;
}

@media (max-width: 767px) {
  .books-view {
    padding: v-bind(LAYOUT.VIEW_PADDING_MOBILE);
  }
}
</style>
