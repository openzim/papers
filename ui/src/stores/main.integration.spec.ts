/**
 * Integration tests for main store
 * Tests complete data fetching flow with axios and error handling
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMainStore } from './main'
import axios from 'axios'
import type { Config } from '@/types'

vi.mock('axios')

describe('Main Store Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Data Fetching', () => {
    it('fetches the books manifest and updates count', async () => {
      const store = useMainStore()
      const mockData = { totalCount: 100, pageSize: 500, totalPages: 1, bookCountByLanguage: {} }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await store.fetchBooksManifest()

      expect(axios.get).toHaveBeenCalledWith('./books.json')
      expect(result).toEqual(mockData)
      expect(store.booksCount).toBe(100)
      expect(store.loading).toBe(false)
      expect(store.errorMessage).toBeNull()
    })

    it('fetches authors and updates count', async () => {
      const store = useMainStore()
      const mockData = { totalCount: 50, authors: [] }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await store.fetchAuthors()

      expect(axios.get).toHaveBeenCalledWith('./authors.json')
      expect(result).toEqual(mockData)
      expect(store.authorsCount).toBe(50)
      expect(store.loading).toBe(false)
      expect(store.errorMessage).toBeNull()
    })

    it('fetches collections and updates count', async () => {
      const store = useMainStore()
      const mockData = { totalCount: 20, collections: [] }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await store.fetchCollections()

      expect(axios.get).toHaveBeenCalledWith('./collections.json')
      expect(result).toEqual(mockData)
      expect(store.collectionsCount).toBe(20)
      expect(store.loading).toBe(false)
      expect(store.errorMessage).toBeNull()
    })

    it.each([
      { method: 'fetchBook' as const, param: '42', url: './books/42.json' },
      {
        method: 'fetchBook' as const,
        param: 'A/B & C?',
        url: './books/A%2FB%20%26%20C%3F.json'
      },
      { method: 'fetchAuthor' as const, param: 'austen-jane', url: './authors/austen-jane.json' },
      { method: 'fetchAuthor' as const, param: 'a#b', url: './authors/a%23b.json' },
      { method: 'fetchCollection' as const, param: 'PR', url: './collections/PR.json' },
      {
        method: 'fetchCollection' as const,
        param: 'Computer/Science & Maths#1?',
        url: './collections/Computer%2FScience%20%26%20Maths%231%3F.json'
      }
    ])('$method fetches single item by ID', async ({ method, param, url }) => {
      const store = useMainStore()
      const mockData = { id: param }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await store[method](param as never)

      expect(axios.get).toHaveBeenCalledWith(url)
      expect(result).toEqual(mockData)
    })

    it('fetches config data', async () => {
      const store = useMainStore()
      const mockConfig: Config = {
        title: 'Test Library',
        description: 'Test source books',
        zimName: 'test-library',
        bookLanguages: ['en'],
        source: {
          slug: 'test-source',
          name: 'Test Source',
          description: 'Test source books'
        },
        theme: {
          formatIcons: { epub: 'epub', html: 'html' },
          routeLabels: {
            home: 'Home',
            works: 'Books',
            authors: 'Authors',
            collections: 'Collections'
          },
          collectionIconStyle: 'classification'
        },
        features: {
          epubReader: true,
          pdfReader: true,
          noscriptFallback: true
        },
        contentInfo: {
          source: 'Test Source',
          collections: null,
          books: null,
          languages: null,
          formats: null,
          dateScraped: '2026-01-01'
        }
      }

      vi.mocked(axios.get).mockResolvedValue({ data: mockConfig })

      const result = await store.fetchConfig()

      expect(axios.get).toHaveBeenCalledWith('./config.json')
      expect(result).toEqual(mockConfig)
    })
  })

  describe('Loading State', () => {
    it('sets loading during fetch', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: { books: [] } }), 50))
      )

      const promise = store.fetchBooksPage('popularity', 0)
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('sets error message on fetch failure', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockRejectedValue(new Error('Network error'))

      await expect(store.fetchBooksPage('popularity', 0)).rejects.toThrow('Network error')

      expect(store.errorMessage).toBe('Network error')
      expect(store.loading).toBe(false)
    })

    it('uses custom error message when error message is empty', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockRejectedValue(new Error(''))

      await expect(store.fetchBooksPage('title', 0)).rejects.toThrow()

      expect(store.errorMessage).toBe('Failed to load books')
    })

    it('clears error message', () => {
      const store = useMainStore()
      store.errorMessage = 'Test error'

      store.clearError()

      expect(store.errorMessage).toBeNull()
    })

    it('clears previous error on successful fetch', async () => {
      const store = useMainStore()
      store.errorMessage = 'Previous error'

      vi.mocked(axios.get).mockResolvedValue({ data: { books: [] } })

      await store.fetchBooksPage('popularity', 0)

      expect(store.errorMessage).toBeNull()
    })

    it('throws error when response data is empty', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockResolvedValue({ data: null })

      await expect(store.fetchBooksPage('popularity', 0)).rejects.toThrow(
        'Empty response from ./books-pages/popularity/0.json'
      )
      expect(store.errorMessage).toContain('Empty response')
    })
  })

  describe('Books pagination', () => {
    it('reads a page from the directory of the sort it belongs to', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockImplementation((url) => {
        if (url === './books-pages/author/3.json') {
          return Promise.resolve({ data: { books: [{ id: '1' }, { id: '2' }] } })
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`))
      })

      expect(await store.fetchBooksPage('author', 3)).toEqual([{ id: '1' }, { id: '2' }])
      expect(axios.get).toHaveBeenCalledTimes(1)
    })

    it('caches the manifest and the book count it carries', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockResolvedValue({
        data: { totalCount: 7, pageSize: 500, totalPages: 1, bookCountByLanguage: { en: 7 } }
      })

      const manifest = await store.fetchBooksManifest()
      const again = await store.fetchBooksManifest()

      expect(again).toEqual(manifest)
      expect(axios.get).toHaveBeenCalledTimes(1)
      expect(store.booksCount).toBe(7)
    })

    it('caches a page without refetching it', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockImplementation((url) =>
        Promise.resolve({
          data:
            url === './books-pages/popularity/0.json'
              ? { books: [{ id: '1' }, { id: '2' }] }
              : { totalCount: 4, pageSize: 2, totalPages: 2 }
        })
      )

      const first = await store.fetchBooksPage('popularity', 0)
      const second = await store.fetchBooksPage('popularity', 0)

      expect(second).toBe(first)
      expect(axios.get).toHaveBeenCalledTimes(1)
    })

    it('keeps the pages of the sort being browsed and drops the others', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockImplementation((url) =>
        Promise.resolve({ data: { books: [{ id: url }] } })
      )

      const firstPopularity = await store.fetchBooksPage('popularity', 0)
      await store.fetchBooksPage('popularity', 1)
      expect(await store.fetchBooksPage('popularity', 0)).toBe(firstPopularity)
      expect(axios.get).toHaveBeenCalledTimes(2)

      await store.fetchBooksPage('title', 0)
      await store.fetchBooksPage('popularity', 0)

      expect(vi.mocked(axios.get).mock.calls.map(([url]) => url)).toEqual([
        './books-pages/popularity/0.json',
        './books-pages/popularity/1.json',
        './books-pages/title/0.json',
        './books-pages/popularity/0.json'
      ])
    })
  })

  describe('Response Caching', () => {
    it('returns cached authors without refetching', async () => {
      const store = useMainStore()
      const mockData = { totalCount: 50, authors: [{ id: 'a1', name: 'Author 1' }] }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      await store.fetchAuthors()
      expect(axios.get).toHaveBeenCalledTimes(1)

      const result2 = await store.fetchAuthors()
      expect(axios.get).toHaveBeenCalledTimes(1)
      expect(result2).toEqual(mockData)
    })

    it('returns cached collections without refetching', async () => {
      const store = useMainStore()
      const mockData = { totalCount: 20, collections: [{ id: 'PR', bookCount: 5 }] }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      await store.fetchCollections()
      expect(axios.get).toHaveBeenCalledTimes(1)

      const result2 = await store.fetchCollections()
      expect(axios.get).toHaveBeenCalledTimes(1)
      expect(result2).toEqual(mockData)
    })

    it('does not cache single item fetches', async () => {
      const store = useMainStore()
      const mockData = { id: '42', title: 'Book 42' }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      await store.fetchBook('42')
      await store.fetchBook('42')

      expect(axios.get).toHaveBeenCalledTimes(2)
    })
  })

  describe('Request Deduplication', () => {
    it('deduplicates identical concurrent requests', async () => {
      const store = useMainStore()
      const mockData = { books: [{ id: '1' }] }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const [result1, result2, result3] = await Promise.all([
        store.fetchBooksPage('popularity', 0),
        store.fetchBooksPage('popularity', 0),
        store.fetchBooksPage('popularity', 0)
      ])

      expect(axios.get).toHaveBeenCalledTimes(1)
      expect(result1).toEqual(mockData.books)
      expect(result2).toBe(result1)
      expect(result3).toBe(result1)
    })

    it('allows different requests concurrently', async () => {
      const store = useMainStore()
      vi.mocked(axios.get).mockImplementation((url) => {
        if (url.startsWith('./books-pages/')) {
          return Promise.resolve({ data: { books: [] } })
        }
        return Promise.resolve({ data: { totalCount: 0, authors: [] } })
      })

      await Promise.all([store.fetchBooksPage('popularity', 0), store.fetchAuthors()])

      expect(axios.get).toHaveBeenCalledTimes(2)
    })
  })
})
