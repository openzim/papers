/**
 * TypeScript interfaces for Author-related data structures
 * Matches the scraper's source-neutral JSON schemas.
 */

import type { BookPreview } from './Book'

/** Minimal author reference, embedded inside a BookPreview. */
export interface AuthorRef {
  id: string
  /** Full name as shown to readers. */
  displayName: string
  /** Last name alone; not for display. Tiebreak on `displayName` when sorting. */
  sortName: string
}

export interface AuthorPreview extends AuthorRef {
  bookCount: number
  totalPopularity?: number
  portraitPath?: string | null
  // Per-language breakdown, used by useLanguageFilter.
  languages: string[]
  bookCountByLanguage: Record<string, number>
  totalPopularityByLanguage?: Record<string, number>
}

export interface Author extends AuthorPreview {
  birthYear: string | null
  deathYear: string | null
  bio?: string | null
  portraitPath?: string | null
  webpageResource?: string | null
}

export interface AuthorDetail extends Author {
  books: BookPreview[]
}

export interface Authors {
  authors: AuthorPreview[]
  totalCount: number
}
