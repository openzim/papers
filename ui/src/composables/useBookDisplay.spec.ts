/**
 * Unit tests for useBookDisplay composable
 * Focuses on forcing alphabetical sorting for sources without popularity and
 * on reading a window of the catalog rather than all of it
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useBookDisplay } from './useBookDisplay'
import type { CatalogWindow, SortState } from './useBooksWindow'
import { useMainStore } from '@/stores/main'
import type { BookPreview, SortOption, SortOrder } from '@/types'

function book(id: string, title: string, popularity: number): BookPreview {
  return {
    id,
    title,
    author: {
      id: `author-${id}`,
      displayName: `Author ${id}`,
      sortName: id
    },
    languages: ['en'],
    popularity,
    flames: 1,
    coverPath: null,
    primaryCollection: null
  }
}

const BOOKS = [book('z', 'Zebra', 1), book('a', 'Apple', 99), book('m', 'Mango', 50)]

// useBookDisplay uses lifecycle hooks, so it has to be exercised inside a component
function mountBookDisplay(books: BookPreview[], catalog?: CatalogWindow, sort?: SortState) {
  let display!: ReturnType<typeof useBookDisplay>
  mount(
    defineComponent({
      setup() {
        display = useBookDisplay(ref(books), catalog, sort)
        return () => h('div')
      }
    })
  )
  return display
}

function sortState(sortBy: SortOption, sortOrder: SortOrder): SortState {
  return { sortBy: ref(sortBy), sortOrder: ref(sortOrder) }
}

function catalogWindow(): CatalogWindow {
  return {
    total: () => 900,
    hasMore: () => true,
    loadMore: vi.fn(async () => undefined)
  }
}

describe('useBookDisplay', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function setConfigPopularity(popularity: boolean) {
    useMainStore().config = {
      title: 'Test',
      description: null,
      zimName: 'test',
      bookLanguages: ['en'],
      source: { slug: 'test', name: 'Test', description: 'Test' },
      theme: { formatIcons: {}, routeLabels: {}, collectionIconStyle: 'classification' },
      features: {
        epubReader: true,
        pdfReader: true,
        noscriptFallback: true,
        hasPopularity: popularity
      },
      contentInfo: {
        source: 'Test',
        collections: null,
        books: null,
        languages: null,
        formats: null,
        dateScraped: '2026-01-01'
      }
    }
  }

  it('sorts by popularity by default when the source has popularity', () => {
    setConfigPopularity(true)

    const { sortBy, sortOrder } = mountBookDisplay(BOOKS)

    expect(sortBy.value as SortOption).toBe('popularity')
    expect(sortOrder.value as SortOrder).toBe('desc')
  })

  it('sorts alphabetically when the source has no popularity', () => {
    setConfigPopularity(false)

    const { sortBy, sortOrder, sortedBooks } = mountBookDisplay(BOOKS)

    expect(sortBy.value as SortOption).toBe('title')
    expect(sortOrder.value as SortOrder).toBe('asc')
    expect(sortedBooks.value.map((b) => b.title)).toEqual(['Apple', 'Mango', 'Zebra'])
  })

  it('forces alphabetical when config resolves to no popularity after setup', async () => {
    const { sortBy, sortOrder } = mountBookDisplay(BOOKS)
    expect(sortBy.value as SortOption).toBe('popularity')

    setConfigPopularity(false)
    await nextTick()

    expect(sortBy.value as SortOption).toBe('title')
    expect(sortOrder.value as SortOrder).toBe('asc')
  })

  it('counts the catalog a window is part of, not the window itself', () => {
    setConfigPopularity(true)

    const display = mountBookDisplay(BOOKS, catalogWindow())

    expect(display.sortedBooks.value).toHaveLength(3)
    expect(display.catalogTotal.value).toBe(900)
  })

  it('still has books to show when the window has further pages', () => {
    setConfigPopularity(true)

    const display = mountBookDisplay(BOOKS, catalogWindow())

    expect(display.hasMoreBooks.value).toBe(true)
  })

  it('sorts the way the caller that owns the sort state asks for', async () => {
    setConfigPopularity(true)
    const sort = sortState('title', 'asc')

    const display = mountBookDisplay(BOOKS, catalogWindow(), sort)
    expect(display.sortedBooks.value.map((b) => b.title)).toEqual(['Apple', 'Mango', 'Zebra'])

    sort.sortOrder.value = 'desc'
    await nextTick()

    expect(display.sortedBooks.value.map((b) => b.title)).toEqual(['Zebra', 'Mango', 'Apple'])
  })

  it('leaves a sort reset to the caller that owns the sort state', async () => {
    setConfigPopularity(true)
    const sort = sortState('popularity', 'desc')
    const display = mountBookDisplay(BOOKS, catalogWindow(), sort)

    setConfigPopularity(false)
    await nextTick()

    expect(display.sortBy.value).toBe('popularity')
    expect(sort.sortBy.value).toBe('popularity')
  })
})
