import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type {
  BooksManifest,
  BooksPage,
  Book,
  BookPreview,
  Authors,
  AuthorDetail,
  Collections,
  Collection,
  Config,
  SortOption
} from '@/types'

export const useMainStore = defineStore('main', () => {
  const errorMessage = ref<string | null>(null)
  const loading = ref(false)
  const pendingRequests = new Map<string, Promise<unknown>>()
  const loadingCount = ref(0)

  const booksCount = ref(0)
  const authorsCount = ref(0)
  const collectionsCount = ref(0)

  const currentBook = ref<Book | null>(null)
  const currentAuthor = ref<AuthorDetail | null>(null)
  const config = ref<Config | null>(null)

  // null = all languages. Lives here (not per-view) so it applies site-wide.
  const selectedLanguage = ref<string | null>(null)

  // Cached list data to avoid refetching across views
  const bookPages = new Map<number, BookPreview[]>()
  let cachedSort: SortOption | null = null
  const booksManifest = ref<BooksManifest | null>(null)
  const authors = ref<Authors | null>(null)
  const collections = ref<Collections | null>(null)

  async function fetchWithDeduplication<T>(url: string): Promise<T> {
    const existing = pendingRequests.get(url)
    if (existing) {
      return existing as Promise<T>
    }

    const request = axios
      .get<T>(url)
      .then((response) => {
        if (!response.data) {
          throw new Error(`Empty response from ${url}`)
        }
        return response.data
      })
      .finally(() => {
        pendingRequests.delete(url)
      })

    pendingRequests.set(url, request)
    return request
  }

  async function fetchData<T>(url: string, errorMsg: string): Promise<T> {
    try {
      loadingCount.value++
      loading.value = true
      errorMessage.value = null
      return await fetchWithDeduplication<T>(url)
    } catch (error) {
      const message = (error instanceof Error ? error.message : String(error)) || errorMsg
      errorMessage.value = message
      throw error
    } finally {
      loadingCount.value--
      loading.value = loadingCount.value > 0
    }
  }

  async function fetchList<T extends { totalCount: number }>(
    url: string,
    errorMsg: string,
    countRef: { value: number },
    cacheRef: { value: T | null }
  ): Promise<T> {
    if (cacheRef.value) {
      return cacheRef.value
    }
    const result = await fetchData<T>(url, errorMsg)
    countRef.value = result.totalCount
    cacheRef.value = result
    return result
  }

  async function fetchBooksManifest(): Promise<BooksManifest> {
    if (booksManifest.value) {
      return booksManifest.value
    }
    booksManifest.value = await fetchData<BooksManifest>('./books.json', 'Failed to load books')
    booksCount.value = booksManifest.value.totalCount
    return booksManifest.value
  }

  // books-pages holds one page set per sort option value. Only the set being
  // browsed is kept; switching sort drops the previous one from memory.
  async function fetchBooksPage(sort: SortOption, page: number): Promise<BookPreview[]> {
    if (cachedSort !== sort) {
      bookPages.clear()
      cachedSort = sort
    }
    const cached = bookPages.get(page)
    if (cached) {
      return cached
    }
    const result = await fetchData<BooksPage>(
      `./books-pages/${sort}/${page}.json`,
      'Failed to load books'
    )
    bookPages.set(page, result.books)
    return result.books
  }

  function fetchBook(id: string) {
    currentBook.value = null
    return fetchData<Book>(
      `./books/${encodeURIComponent(id)}.json`,
      `Failed to load book ${id}`
    ).then((book) => {
      currentBook.value = book
      return book
    })
  }

  async function fetchAuthors() {
    return fetchList<Authors>('./authors.json', 'Failed to load authors', authorsCount, authors)
  }

  function fetchAuthor(id: string) {
    currentAuthor.value = null
    return fetchData<AuthorDetail>(
      `./authors/${encodeURIComponent(id)}.json`,
      `Failed to load author ${id}`
    ).then((author) => {
      currentAuthor.value = author
      return author
    })
  }

  async function fetchCollections() {
    return fetchList<Collections>(
      './collections.json',
      'Failed to load collections',
      collectionsCount,
      collections
    )
  }

  function fetchCollection(id: string) {
    return fetchData<Collection>(
      `./collections/${encodeURIComponent(id)}.json`,
      `Failed to load collection ${id}`
    )
  }

  async function fetchConfig() {
    if (config.value) {
      return config.value
    }
    config.value = await fetchData<Config>('./config.json', 'Failed to load config')
    return config.value
  }

  function clearError() {
    errorMessage.value = null
  }

  return {
    currentBook,
    currentAuthor,
    config,
    selectedLanguage,
    errorMessage,
    loading,
    booksCount,
    authorsCount,
    collectionsCount,
    fetchBooksManifest,
    fetchBooksPage,
    fetchBook,
    fetchAuthors,
    fetchAuthor,
    fetchCollections,
    fetchCollection,
    fetchConfig,
    clearError
  }
})
