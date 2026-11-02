import { describe, expect, it, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'

import SelectedBooksSection from './SelectedBooksSection.vue'
import { useMainStore } from '@/stores/main'
import type { BookPreview } from '@/types'

const books: BookPreview[] = [
  {
    id: 'first',
    title: 'First three-flame book',
    author: {
      id: 'author-1',
      name: 'First Author',
      firstName: 'First',
      lastName: 'Author',
      bookCount: 1,
      totalPopularity: 10
    },
    languages: ['en'],
    popularity: 10,
    flames: 3,
    coverPath: null,
    primaryCollection: null
  },
  {
    id: 'highest',
    title: 'Highest raw popularity',
    author: {
      id: 'author-2',
      name: 'Second Author',
      firstName: 'Second',
      lastName: 'Author',
      bookCount: 1,
      totalPopularity: 100
    },
    languages: ['en'],
    popularity: 100,
    flames: 3,
    coverPath: null,
    primaryCollection: null
  }
]

describe('SelectedBooksSection', () => {
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

  it('features the work with the highest raw popularity within a flame bin', () => {
    const i18n = createI18n({
      legacy: false,
      locale: 'en',
      messages: { en: { home: { mostPopular: 'Most popular' } } }
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: []
    })

    const wrapper = mount(SelectedBooksSection, {
      props: { books },
      global: {
        plugins: [i18n, router],
        stubs: {
          BooksGrid: true,
          FireRating: true,
          SectionHeader: true
        }
      }
    })

    expect(wrapper.find('.featured-book__title').text()).toBe('Highest raw popularity')
  })

  it('hides the most popular book and shows no flames without popularity', async () => {
    setConfigPopularity(false)
    const i18n = createI18n({
      legacy: false,
      locale: 'en',
      messages: { en: { home: { mostPopular: 'Most popular' } } }
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: []
    })

    const wrapper = mount(SelectedBooksSection, {
      props: { books },
      global: {
        plugins: [i18n, router],
        stubs: {
          BooksGrid: true,
          SectionHeader: true
        }
      }
    })

    expect(wrapper.find('.selected-books-section__featured').exists()).toBe(false)
    expect(wrapper.find('.featured-book__label').exists()).toBe(false)
  })
})
