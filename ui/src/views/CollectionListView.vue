<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useMainStore } from '@/stores/main'
import type { BookPreview, CollectionPreview } from '@/types'
import BookDisplay from '@/components/book/BookDisplay.vue'
import BackToTopButton from '@/components/common/BackToTopButton.vue'
import CollectionSidebar from '@/components/collection/CollectionSidebar.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { useListLoader } from '@/composables/useListLoader'
import { useBooksWindow } from '@/composables/useBooksWindow'
import { useLanguageFilter } from '@/composables/useLanguageFilter'
import { matchesLanguage, withLanguageCounts } from '@/utils/language-filter'
import { LAYOUT } from '@/constants/theme'
import { MESSAGES } from '@/constants/messages'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const main = useMainStore()
const { selectedLanguage } = useLanguageFilter()

const {
  items: collections,
  loading: collectionsLoading,
  loadItems: loadCollections
} = useListLoader<CollectionPreview, { collections: CollectionPreview[]; totalCount: number }>(
  () => main.fetchCollections(),
  'collections'
)

loadCollections()

const activeCollectionId = computed(() => {
  const id = route.query.collection as string | undefined
  return id || null
})
const collectionIconStyle = computed(
  () => main.config?.theme.collectionIconStyle || 'classification'
)

const {
  books: catalogBooks,
  loading: catalogLoading,
  catalog,
  sort,
  load: loadCatalog,
  loadCounts
} = useBooksWindow(() => activeCollectionId.value === null)

const collectionBooks = ref<BookPreview[]>([])
const booksLoading = ref(false)

const sidebarCollections = computed(() =>
  withLanguageCounts(collections.value, selectedLanguage.value)
)

const totalBooks = computed(() => catalog.total())

const filteredCollectionBooks = computed(() =>
  selectedLanguage.value === null
    ? collectionBooks.value
    : collectionBooks.value.filter((book) =>
        matchesLanguage(book.languages, selectedLanguage.value)
      )
)

async function loadBooks(id: string | null) {
  booksLoading.value = true
  try {
    if (id) {
      await loadCounts()
      const collection = await main.fetchCollection(id)
      if (activeCollectionId.value !== id) return
      collectionBooks.value = collection.books
    } else {
      await loadCatalog()
    }
  } catch {
    if (activeCollectionId.value === id) {
      collectionBooks.value = []
    }
  } finally {
    if (activeCollectionId.value === id) {
      booksLoading.value = false
    }
  }
}

watch([activeCollectionId, selectedLanguage], () => loadBooks(activeCollectionId.value), {
  immediate: true
})

function selectCollection(id: string | null) {
  const query = id
    ? { ...route.query, collection: id }
    : Object.fromEntries(Object.entries(route.query).filter(([key]) => key !== 'collection'))
  router.push({ query })
}
</script>

<template>
  <div class="collection-view-view">
    <div class="collection-view-view__layout">
      <collection-sidebar
        :collections="sidebarCollections"
        :active-id="activeCollectionId"
        :total-books="totalBooks"
        :icon-style="collectionIconStyle"
        @select="selectCollection"
      />

      <div class="collection-view-view__content">
        <div
          v-if="collectionsLoading || booksLoading || catalogLoading"
          class="collection-view-view__loading"
        >
          <loading-spinner :message="t('common.loading')" />
        </div>

        <template v-else-if="activeCollectionId">
          <book-display
            v-if="filteredCollectionBooks.length > 0"
            :books="filteredCollectionBooks"
            :columns="4"
            variant="wide"
            type="books"
          />
          <empty-state v-else :message="t(MESSAGES.NO_BOOKS)" type="info" />
        </template>

        <template v-else>
          <book-display
            v-if="catalogBooks.length > 0"
            :books="catalogBooks"
            :catalog="catalog"
            :sort="sort"
            :columns="4"
            variant="wide"
            type="books"
          />
          <empty-state v-else :message="t(MESSAGES.NO_BOOKS)" type="info" />
        </template>
      </div>
    </div>

    <back-to-top-button />
  </div>
</template>

<style scoped>
.collection-view-view {
  padding: v-bind(LAYOUT.VIEW_PADDING);
  max-width: v-bind(LAYOUT.MAX_CONTENT_WIDTH);
  margin: 0 auto;
}

.collection-view-view__layout {
  display: flex;
  justify-content: space-between;
}

.collection-view-view__content {
  flex: 1;
  padding-inline-start: 1.5rem;
  min-width: 0;
}

.collection-view-view__loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

@media (max-width: 767px) {
  .collection-view-view {
    padding: v-bind(LAYOUT.VIEW_PADDING_MOBILE);
  }

  .collection-view-view__layout {
    flex-direction: column;
  }

  .collection-view-view__content {
    padding: 1.5rem 0rem;
  }
}
</style>
