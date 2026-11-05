/**
 * TypeScript interfaces for Book-related data structures
 * Matches the scraper's source-neutral JSON schemas.
 */

import type { AuthorRef, Author } from './Author'

export interface BookFormat {
  format: string // "html", "epub", "pdf"
  path: string // ZIM path to file
  available: boolean
}

export interface BookPreview {
  id: string
  title: string
  author: AuthorRef
  languages: string[]
  popularity: number // Source-specific ranking score
  flames: number // Flame rating (0-3)
  coverPath: string | null
  primaryCollection: string | null
  availableFormats?: string[]
  /** Short excerpt only; the full text is on the Book detail type. */
  description?: string | null
}

export interface Book extends Omit<BookPreview, 'author'> {
  subtitle: string | null
  author: Author // Full author instead of preview
  license: string
  licenseId?: string | null // Creative Commons identifier (e.g. "CC-BY-SA-3.0") when license names one
  formats: BookFormat[]
  description: string | null
  published: string | null
}

export interface Books {
  books: BookPreview[]
  totalCount: number
}

/** Pagination manifest served at books.json; the catalog itself is chunked
 * into books-pages/{page}.json files of `pageSize` BookPreview each. */
export interface BooksManifest {
  totalCount: number
  pageSize: number
  totalPages: number
}

export interface BooksPage {
  books: BookPreview[]
}
