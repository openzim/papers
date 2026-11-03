import type { BookPreview } from './Book'

export interface CollectionPreview {
  id: string
  name: string
  bookCount: number
  totalPopularity?: number
  // Same per-language breakdown as `AuthorPreview`, and for the same reason.
  languages: string[]
  bookCountByLanguage: Record<string, number>
  totalPopularityByLanguage?: Record<string, number>
}

export interface Collection extends CollectionPreview {
  books: BookPreview[]
}

export interface Collections {
  collections: CollectionPreview[]
  totalCount: number
}
