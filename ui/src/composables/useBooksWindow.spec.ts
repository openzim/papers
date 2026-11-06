/**
 * Unit tests for useBooksWindow
 * Covers growing one sort's page set at a time and switching between the sets
 * the scraper emits per sort criterion.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { useBooksWindow } from './useBooksWindow'
import { useMainStore } from '@/stores/main'
import type { BookPreview, BooksManifest, SortOption } from '@/types'

function book(id: string, ...languages: string[]): BookPreview {
  return {
    id,
    title: `Book ${id}`,
    author: { id: 'a', displayName: 'Author', sortName: 'Author' },
    languages: ['en', ...languages],
    popularity: Number(id),
    flames: 0,
    coverPath: null,
    primaryCollection: null
  }
}

const PAGES: Record<SortOption, BookPreview[][]> = {
  popularity: [[book('5', 'fr'), book('4')], [book('3'), book('2', 'fr')], [book('1')]],
  title: [[book('1'), book('2', 'fr')], [book('3'), book('4')], [book('5', 'fr')]],
  author: [[book('3'), book('4')], [book('1'), book('5', 'fr')], [book('2', 'fr')]]
}

const MANIFEST: BooksManifest = {
  totalCount: 5,
  pageSize: 2,
  totalPages: 3,
  bookCountByLanguage: { en: 5, fr: 2 }
}

const ALL_IDS = ['1', '2', '3', '4', '5']

describe('useBooksWindow', () => {
  let store: ReturnType<typeof useMainStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useMainStore()
    vi.spyOn(store, 'fetchBooksManifest').mockResolvedValue(MANIFEST)
    vi.spyOn(store, 'fetchBooksPage').mockImplementation(
      async (sort: SortOption, page: number) => PAGES[sort][page] ?? []
    )
  })

  function fetchedPages(): string[] {
    return vi.mocked(store.fetchBooksPage).mock.calls.map(([sort, page]) => `${sort}/${page}`)
  }

  it('opens with the first page of the most-popular set', async () => {
    const { books, catalog, load } = useBooksWindow()

    await load()

    expect(books.value.map((b) => b.id)).toEqual(['5', '4'])
    expect(catalog.total()).toBe(5)
    expect(catalog.hasMore()).toBe(true)
    expect(fetchedPages()).toEqual(['popularity/0'])
  })

  it('appends pages of the same set as the reader reaches the end', async () => {
    const { books, catalog, load } = useBooksWindow()
    await load()

    await catalog.loadMore()
    await catalog.loadMore()

    expect(books.value.map((b) => b.id)).toEqual(ALL_IDS.slice().reverse())
    expect(catalog.hasMore()).toBe(false)
    expect(fetchedPages()).toEqual(['popularity/0', 'popularity/1', 'popularity/2'])
  })

  it('loads nothing but the manifest when only counts are needed', async () => {
    const { books, catalog, loadCounts } = useBooksWindow()

    await loadCounts()

    expect(store.fetchBooksPage).not.toHaveBeenCalled()
    expect(books.value).toEqual([])
    expect(catalog.total()).toBe(5)
  })

  it('counts the selected language from the manifest', async () => {
    const { catalog, load } = useBooksWindow(() => false)
    await load()

    store.selectedLanguage = 'fr'

    expect(catalog.total()).toBe(2)
  })

  it('filters the pages it streams and keeps their order', async () => {
    store.selectedLanguage = 'fr'
    const { books, catalog, load } = useBooksWindow()

    await load()
    await catalog.loadMore()

    expect(books.value.map((b) => b.id)).toEqual(['5', '2'])
    expect(fetchedPages()).toEqual(['popularity/0', 'popularity/1'])
  })

  it('reads past pages the selected language has no books on', async () => {
    store.selectedLanguage = 'fr'
    const { books, catalog, load } = useBooksWindow()

    await load()
    expect(books.value.map((b) => b.id)).toEqual(['5'])

    store.selectedLanguage = 'de'
    await flushPromises()

    expect(books.value).toEqual([])
    expect(catalog.hasMore()).toBe(false)
  })

  it('switches to the other criterion directory when the reader sorts', async () => {
    const { books, sort, load } = useBooksWindow()
    await load()

    sort.sortBy.value = 'title'
    sort.sortOrder.value = 'asc'
    await flushPromises()

    expect(books.value.map((b) => b.id)).toEqual(['1', '2'])
    expect(fetchedPages()).toEqual(['popularity/0', 'title/0'])
  })

  it('spins while the books of a new sort order arrive', async () => {
    const { books, loading, sort, load } = useBooksWindow()
    await load()

    let pageArrived!: () => void
    const arriving = new Promise<void>((resolve) => (pageArrived = resolve))
    vi.spyOn(store, 'fetchBooksPage').mockImplementation(async (sort_, page) => {
      await arriving
      return PAGES[sort_][page] ?? []
    })

    sort.sortBy.value = 'author'
    sort.sortOrder.value = 'asc'
    await nextTick()

    expect(loading.value).toBe(true)
    expect(books.value).toEqual([])

    pageArrived()
    await flushPromises()

    expect(loading.value).toBe(false)
    expect(books.value.map((b) => b.id)).toEqual(['3', '4'])
  })

  it('fills once: a reload of a window that has books fetches no page', async () => {
    const { books, load } = useBooksWindow()

    await load()
    await load()

    expect(books.value).toHaveLength(2)
    expect(store.fetchBooksPage).toHaveBeenCalledOnce()
  })

  it('stays on the manifest while the view is not browsing the catalog', async () => {
    const { catalog, load } = useBooksWindow(() => false)

    await load()

    expect(store.fetchBooksPage).not.toHaveBeenCalled()
    expect(catalog.total()).toBe(5)
  })
})
