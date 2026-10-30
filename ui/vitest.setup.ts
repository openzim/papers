import { config } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createI18n } from 'vue-i18n'
import en from '../locales/en.json'

// Mock browser APIs
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.IntersectionObserver = class IntersectionObserver {
  readonly root = null
  readonly rootMargin = ''
  readonly thresholds = []

  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return []
  }
}

// jsdom has no visualViewport; Vuetify's VOverlay location strategies read it
// to position dialogs/menus.
globalThis.visualViewport ??= {
  width: window.innerWidth,
  height: window.innerHeight,
  offsetLeft: 0,
  offsetTop: 0,
  pageLeft: 0,
  pageTop: 0,
  scale: 1,
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => true
} as unknown as VisualViewport

// Create Vuetify instance for tests
const vuetify = createVuetify({
  components,
  directives
})

// Create i18n instance for tests with minimal English messages
const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en: {
      common: {
        filterByTitle: 'Filter by {title}',
        clearAllSelections: 'Clear all selections',
        selectAll: 'Select all',
        clear: 'Clear',
        close: 'Close',
        all: 'All',
        filter: 'filter',
        selected: 'selected',
        format: 'Format',
        language: 'Language',
        sort: 'Sort',
        sortPopularity: 'Popularity',
        sortTitle: 'Title'
      },
      author: {
        bookCount: '{n} book | {n} books'
      },
      book: {
        unknown: 'Unknown',
        downloadsCount: '{n} downloads'
      },
      collection: {
        bookCount: '{n} book | {n} books'
      },
      // The real messages, so license tests fail when a key is renamed or removed
      licenses: en.common.licenses,
      zimInfo: {
        trigger: 'Information about this ZIM',
        title: 'Information about this ZIM',
        source: 'Source',
        collections: { one: 'Collection', other: 'Collections' },
        books: { one: 'Book', other: 'Books' },
        language: { one: 'Language', other: 'Languages' },
        formats: { one: 'Format', other: 'Formats' },
        dateScraped: 'Date scraped'
      },
      messages: {
        noBooksForAuthor: 'No books available for this author',
        noBooksInCollection: 'No books in this collection',
        noBooks: 'No books found',
        noAuthors: 'No authors found',
        noCollections: 'No collections found',
        noLanguages: 'No languages available',
        noFormats: 'No formats available'
      }
    }
  }
})

// Set global mount options
config.global.plugins = [vuetify, i18n]
