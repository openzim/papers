/**
 * Unit tests for useBookDisplay composable
 * Focuses on forcing alphabetical sorting for sources without popularity
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useBookDisplay } from './useBookDisplay'
import { useMainStore } from '@/stores/main'
import type { BookPreview, SortOption, SortOrder } from '@/types'

function book(id: string, title: string, popularity: number): BookPreview {
  return {
    id,
    title,
    author: {
      id: `author-${id}`,
      displayName: `Author ${id}`,
      sortName: id,
      bookCount: 1,
      totalPopularity: popularity
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
function mountBookDisplay(books: BookPreview[]) {
  let display!: ReturnType<typeof useBookDisplay>
  mount(
    defineComponent({
      setup() {
        display = useBookDisplay(ref(books))
        return () => h('div')
      }
    })
  )
  return display
}

describe('useBookDisplay', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function setConfigPopularity(popularity: boolean) {
    useMainStore().config = {
      title: 'Test',
      description: null,
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
})
