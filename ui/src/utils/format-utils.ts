import { getLanguageName } from '@/utils/language-names'

export function formatAuthorLifespan(birthYear: string | null, deathYear: string | null): string {
  if (birthYear && deathYear) {
    return `${birthYear} - ${deathYear}`
  }
  if (birthYear) {
    return `${birthYear} -`
  }
  if (deathYear) {
    return `- ${deathYear}`
  }
  return ''
}

export function compareAuthorNames(
  a: { sortName: string; displayName: string },
  b: { sortName: string; displayName: string }
): number {
  return a.sortName.localeCompare(b.sortName) || a.displayName.localeCompare(b.displayName)
}

export function formatLabel(format: string): string {
  return format === 'epub' ? 'ePUB' : format.toUpperCase()
}

/** Format an ISO 8601 date-only string (e.g. "2026-09-23") in the given locale. */
export function formatScrapeDate(isoDate: string, locale: string): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  if (!year || !month || !day) return isoDate
  const date = new Date(year, month - 1, day)
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)
}

export function formatLanguages(languages: string[], options?: { uiLocale?: string }): string {
  const locale = options?.uiLocale || 'en'

  return languages.map((code) => getLanguageName(code, locale)).join(', ')
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : plural || `${singular}s`
}

export function extractUniqueValues<T>(items: T[], getter: (item: T) => string[]): string[] {
  const values = new Set<string>()
  items.forEach((item) => {
    getter(item).forEach((value) => values.add(value))
  })
  return Array.from(values).sort()
}

export function normalizeImagePath(path: string): string {
  return normalizeZimPath(path)
}

/** Make an archive-relative ZIM path unambiguously relative to the app. */
export function normalizeZimPath(path: string): string {
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(path) || /^(?:blob|data|mailto|tel):/i.test(path)) {
    return path
  }
  if (path.startsWith('/')) return path
  return path.startsWith('./') ? path : `./${path}`
}
