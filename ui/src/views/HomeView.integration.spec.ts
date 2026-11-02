/**
 * Integration tests for HomeView
 * Tests that the Popular Collections section is hidden, and the Selected
 * Books section is moved ahead of Selected Authors, when the ZIM only has
 * a single collection.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import HomeView from './HomeView.vue'
import { useMainStore } from '@/stores/main'
import type { Collections, Authors, Books } from '@/types'

const mockCollectionsData: Collections = {
  totalCount: 2,
  collections: [
    { id: 'PR', name: 'English literature', bookCount: 150, totalPopularity: 10 },
    { id: 'PS', name: 'American literature', bookCount: 200, totalPopularity: 5 }
  ]
}

const mockAuthorsData: Authors = {
  totalCount: 1,
  authors: [
    {
      id: '1',
      name: 'Jane Austen',
      firstName: 'Jane',
      lastName: 'Austen',
      bookCount: 1,
      totalPopularity: 10
    }
  ]
}

const mockBooksData: Books = {
  totalCount: 1,
  books: [
    {
      id: '1',
      title: 'Emma',
      author: { id: '1', name: 'Jane Austen', firstName: 'Jane', lastName: 'Austen', bookCount: 1 },
      languages: ['en'],
      popularity: 10,
      flames: 2,
      coverPath: null,
      primaryCollection: 'PR'
    }
  ]
}

function setHasMultipleCollections(store: ReturnType<typeof useMainStore>, value: boolean) {
  store.config = {
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
      hasMultipleCollections: value
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

describe('HomeView', () => {
  let router: ReturnType<typeof createRouter>
  let pinia: ReturnType<typeof createPinia>
  let store: ReturnType<typeof useMainStore>

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)
    store = useMainStore()
    router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: HomeView }]
    })
    await router.push('/')
    await router.isReady()
  })

  const mountHome = async () => {
    vi.spyOn(store, 'fetchCollections').mockResolvedValue(mockCollectionsData)
    vi.spyOn(store, 'fetchCollection').mockResolvedValue({
      ...mockCollectionsData.collections[0],
      books: mockBooksData.books
    })
    vi.spyOn(store, 'fetchAuthors').mockResolvedValue(mockAuthorsData)
    vi.spyOn(store, 'fetchBooks').mockResolvedValue(mockBooksData)

    const wrapper = mount(HomeView, { global: { plugins: [pinia, router] } })
    await flushPromises()
    return wrapper
  }

  function sectionOrder(wrapper: Awaited<ReturnType<typeof mountHome>>) {
    const selector = '.popular-collections-bar, .selected-authors-carousel, .selected-books-section'
    return wrapper.findAll(selector).map((el) => el.classes()[0])
  }

  it('shows Popular Collections before Authors before Books when there are multiple collections', async () => {
    setHasMultipleCollections(store, true)

    const wrapper = await mountHome()

    expect(store.fetchCollections).toHaveBeenCalled()
    expect(sectionOrder(wrapper)).toEqual([
      'popular-collections-bar',
      'selected-authors-carousel',
      'selected-books-section'
    ])
  })

  it('hides Popular Collections and shows Books before Authors when there is a single collection', async () => {
    setHasMultipleCollections(store, false)

    const wrapper = await mountHome()

    expect(store.fetchCollections).not.toHaveBeenCalled()
    expect(sectionOrder(wrapper)).toEqual(['selected-books-section', 'selected-authors-carousel'])
  })
})
