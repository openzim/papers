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

/** Pagination manifest served at books.json; the catalog itself is chunked
 * into books-pages/{order}/{page}.json files of `pageSize` BookPreview each,
 * one set per sort criterion the UI offers. Each set is cut in the direction
 * this UI sorts it by default, so a prefix of the set being browsed is what a
 * reader sees at the top of that sort. */
export interface BooksManifest {
  totalCount: number
  pageSize: number
  totalPages: number
  bookCountByLanguage: Record<string, number>
}

export interface BooksPage {
  books: BookPreview[]
}
