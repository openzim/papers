import { computed, ref, shallowRef, watch, type Ref } from 'vue'
import { useMainStore } from '@/stores/main'
import { useHasPopularity } from '@/composables/useHasPopularity'
import type { BookPreview, BooksManifest, SortOption, SortOrder } from '@/types'
import { matchesLanguage } from '@/utils/language-filter'

/**
 * The part of the books catalog a view is working with right now.
 *
 * `total`/`hasMore` are functions rather than computed refs so that a caller
 * reads them inside its own computed state and keeps tracking the catalog.
 */
export interface CatalogWindow {
  total: () => number
  hasMore: () => boolean
  loadMore: () => Promise<void>
}

/** The reader's sort choice, held by whoever owns the catalog window. */
export interface SortState {
  sortBy: Ref<SortOption>
  sortOrder: Ref<SortOrder>
}

/**
 * Books catalog as a window walking one `books-pages/{sort}/{n}.json` page set
 * at a time, so no view ever merges the catalog.
 *
 * The scraper emits a page set per sort option value, each cut in the
 * direction the UI sorts it by default, so the window is always the prefix the
 * reader would see at the top of the sort they picked. A selected language
 * filters the pages as they arrive: filtering an ordered stream keeps it
 * ordered, so the window stays the correct prefix and only the matching books
 * are held.
 *
 * `sort` is owned here, above the display component, because reloading a
 * different page set shows a spinner and the display unmounts while it is up;
 * a choice made there has to survive that.
 *
 * `isBrowsingCatalog` lets a view that only sometimes shows the catalog (the
 * collections sidebar does this) decline page fetches.
 */
export function useBooksWindow(isBrowsingCatalog: () => boolean = () => true) {
  const main = useMainStore()
  const hasPopularity = useHasPopularity()

  const sortBy = ref<SortOption>(hasPopularity.value ? 'popularity' : 'title')
  const sortOrder = ref<SortOrder>(hasPopularity.value ? 'desc' : 'asc')
  const books = shallowRef<BookPreview[]>([])
  const loading = ref(false)
  const manifest = shallowRef<BooksManifest | null>(null)

  let nextPage = 0

  const selectedLanguage = computed(() => main.selectedLanguage)

  let pending: Promise<void> | null = null

  function run(task: () => Promise<void>): Promise<void> {
    if (!pending) {
      pending = task().then(clearPending, (error) => {
        clearPending()
        console.error(error)
      })
    }
    return pending
  }

  function clearPending() {
    pending = null
  }

  const totalPages = () => manifest.value?.totalPages ?? 0

  const hasMore = () => nextPage < totalPages()

  /** Book count the current language filter selects, precomputed at scrape time. */
  const total = () => {
    const language = selectedLanguage.value
    if (language === null) {
      return manifest.value?.totalCount ?? 0
    }
    return manifest.value?.bookCountByLanguage[language] ?? 0
  }

  async function ensureManifest(): Promise<void> {
    manifest.value = await main.fetchBooksManifest()
  }

  async function appendNextPage(): Promise<void> {
    while (nextPage < totalPages()) {
      const page = await main.fetchBooksPage(sortBy.value, nextPage)
      nextPage += 1
      const matches = filterBooks(page)
      if (matches.length > 0) {
        books.value = [...books.value, ...matches]
        return
      }
    }
  }

  function filterBooks(page: BookPreview[]): BookPreview[] {
    const language = selectedLanguage.value
    return language === null
      ? page
      : page.filter((book) => matchesLanguage(book.languages, language))
  }

  async function fillWindow(): Promise<void> {
    if (!isBrowsingCatalog()) {
      return
    }
    await appendNextPage()
  }

  async function load(): Promise<void> {
    loading.value = true
    try {
      await run(async () => {
        if (!manifest.value) {
          await ensureManifest()
        }
        if (books.value.length === 0) {
          await fillWindow()
        }
      })
    } finally {
      loading.value = false
    }
  }

  /** Fetch the manifest only: enough to state catalog counts, no book loaded. */
  async function loadCounts(): Promise<void> {
    if (manifest.value) {
      return
    }
    loading.value = true
    try {
      await run(ensureManifest)
    } finally {
      loading.value = false
    }
  }

  /** Start the active sort's page set over, showing the spinner in between. */
  async function reload(): Promise<void> {
    books.value = []
    nextPage = 0
    await load()
  }

  async function loadMore(): Promise<void> {
    if (hasMore()) {
      await run(appendNextPage)
    }
  }

  watch([sortBy, selectedLanguage], () => {
    if (!manifest.value || !isBrowsingCatalog()) {
      return
    }
    void reload()
  })

  watch(hasPopularity, (available) => {
    if (!available) {
      sortBy.value = 'title'
      sortOrder.value = 'asc'
    }
  })

  const catalogWindow: CatalogWindow = { total, hasMore, loadMore }
  const sort: SortState = { sortBy, sortOrder }

  return { books, loading, sort, catalog: catalogWindow, load, loadCounts }
}
