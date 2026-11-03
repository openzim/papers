/**
 * Shared logic for the global book-language filter.
 *
 * `selected === null` means "all languages" and every function here is a
 * no-op in that case.
 */

interface LanguageBreakdown {
  bookCount: number
  totalPopularity?: number
  bookCountByLanguage: Record<string, number>
  totalPopularityByLanguage?: Record<string, number>
}

export function matchesLanguage(languages: string[], selected: string | null): boolean {
  return selected === null || languages.includes(selected)
}

/**
 * Filters a list of authors/collections down to the ones having at least one
 * book in the selected language, and swaps their displayed `bookCount` /
 * `totalPopularity` for the language-specific figures the scraper already
 * precomputed — so cards never show an all-languages count once a language
 * is selected.
 */
export function withLanguageCounts<T extends LanguageBreakdown>(
  items: T[],
  selected: string | null
): T[] {
  if (selected === null) {
    return items
  }
  return items
    .filter((item) => (item.bookCountByLanguage[selected] ?? 0) > 0)
    .map((item) => ({
      ...item,
      bookCount: item.bookCountByLanguage[selected] ?? 0,
      totalPopularity: item.totalPopularityByLanguage?.[selected] ?? 0
    }))
}
