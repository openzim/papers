import { ref, computed, watch, nextTick, onMounted, onUnmounted, type Ref } from 'vue'
import type { BookPreview, SortOption, SortOrder } from '@/types'
import type { CatalogWindow, SortState } from '@/composables/useBooksWindow'
import { useInfiniteScroll } from './useInfiniteScroll'
import { useSorting, type SortConfig } from './useSorting'
import { useHasPopularity } from './useHasPopularity'

const DEFAULT_BATCH_SIZE = 20

const sortOptions: SortConfig<BookPreview>[] = [
  {
    value: 'popularity',
    compare: (a, b) => a.popularity - b.popularity
  },
  {
    value: 'title',
    compare: (a, b) => a.title.localeCompare(b.title)
  },
  {
    value: 'author',
    compare: (a, b) => a.author.sortName.localeCompare(b.author.sortName)
  }
]

/**
 * Sort state comes from `sort` when the caller keeps it (the catalog window
 * does, so a reader's choice outlives the spinner shown while a different
 * page set loads). Lists without a catalog own their choice here instead.
 */
export function useBookDisplay(
  books: Ref<BookPreview[]>,
  catalog?: CatalogWindow,
  sort?: SortState
) {
  const hasPopularity = useHasPopularity()
  const ownSort = ref<SortOption>(hasPopularity.value ? 'popularity' : 'title')
  const ownSortOrder = ref<SortOrder>(hasPopularity.value ? 'desc' : 'asc')
  const sortBy = sort?.sortBy ?? ownSort
  const sortOrder = sort?.sortOrder ?? ownSortOrder
  const viewMode = ref<'grid' | 'list'>('grid')

  watch(hasPopularity, (available) => {
    if (!available && !sort) {
      sortBy.value = 'title'
      sortOrder.value = 'asc'
    }
  })

  const isGridView = computed(() => viewMode.value === 'grid')

  const { sortedItems: sortedBooks } = useSorting(() => books.value, sortBy, sortOrder, sortOptions)

  // Infinite scroll
  const {
    displayedItems: displayedBooks,
    hasMore: hasMoreDisplayed,
    loadMore: loadMoreDisplayed,
    reset: infiniteReset
  } = useInfiniteScroll(() => sortedBooks.value, DEFAULT_BATCH_SIZE, { resetOnItemsChange: false })

  const hasMoreBooks = computed(() => hasMoreDisplayed.value || (catalog?.hasMore() ?? false))

  const catalogTotal = computed(() => (catalog ? catalog.total() : sortedBooks.value.length))

  async function loadMoreBooks(): Promise<void> {
    if (hasMoreDisplayed.value) {
      loadMoreDisplayed()
      return
    }
    await catalog?.loadMore()
  }

  const displayedRange = computed(() => `1-${sortedBooks.value.length}`)

  // Infinite scroll sentinel
  const sentinelRef = ref<HTMLElement | null>(null)
  let observer: IntersectionObserver | null = null

  function setupObserver() {
    observer?.disconnect()

    nextTick(() => {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0]?.isIntersecting && hasMoreBooks.value) {
            void loadMoreBooks()
          }
        },
        { rootMargin: '100px' }
      )
      if (sentinelRef.value) {
        observer.observe(sentinelRef.value)
      }
    })
  }

  watch([sortBy, sortOrder], () => {
    infiniteReset()
    setupObserver()
  })

  let sourceLength = books.value.length
  watch(
    () => books.value.length,
    (length) => {
      if (length < sourceLength) {
        infiniteReset()
      }
      sourceLength = length
      setupObserver()
    }
  )

  onMounted(setupObserver)
  onUnmounted(() => {
    observer?.disconnect()
  })

  return {
    // State refs (for v-model binding)
    sortBy,
    sortOrder,
    viewMode,

    // Computed flags
    isGridView,

    // Data
    sortedBooks,
    displayedBooks,
    displayedRange,
    catalogTotal,

    // Infinite scroll
    hasMoreBooks,
    sentinelRef,
    setupObserver
  }
}
