import { supportedLanguages, getPinnedLanguages, type Language } from '@/plugins/i18n'
import { getLanguageName } from './language-names'

export interface LanguageItem {
  id: string
  code: string
  title: string
}

export interface DividerItem {
  id: string
  divider: true
}

export type LanguageListEntry = LanguageItem | DividerItem

export function isDivider(entry: LanguageListEntry): entry is DividerItem {
  return 'divider' in entry
}

// Native name alone when it matches the English name (e.g. "English"),
// otherwise "native - English" (e.g. "Deutsch - German") so the list is
// searchable in both
export function toLanguageItem(language: Language, idPrefix = ''): LanguageItem {
  const english = getLanguageName(language.code, 'en')
  const title = language.display === english ? language.display : `${language.display} - ${english}`
  return { id: `${idPrefix}${language.code}`, code: language.code, title }
}

// The browser language and, for a single-language ZIM, the ZIM's own
// language, pinned first (and still appearing again in their normal sorted
// position below), followed by every supported UI language sorted by native
// name
export function buildLanguageSwitcherItems(bookLanguages: string[] = []): LanguageListEntry[] {
  const fullList = [...supportedLanguages]
    .sort((a, b) => a.display.toLowerCase().localeCompare(b.display.toLowerCase()))
    .map((language) => toLanguageItem(language))

  const pinnedList = getPinnedLanguages(bookLanguages).map((language) =>
    toLanguageItem(language, 'pinned-')
  )

  if (!pinnedList.length) return fullList
  return [...pinnedList, { id: 'divider', divider: true }, ...fullList]
}

// Flattened, deduplicated (by code) matches for a search query, dropping the
// pinned/divider structure - browsing conveniences that don't make sense
// once the list is filtered down to what's actually being searched for
export function filterLanguageItems(items: LanguageListEntry[], query: string): LanguageItem[] {
  const q = query.trim().toLowerCase()
  if (!q) return items.filter((entry): entry is LanguageItem => !isDivider(entry))

  const seen = new Set<string>()
  const matches: LanguageItem[] = []
  for (const entry of items) {
    if (isDivider(entry) || seen.has(entry.code)) continue
    if (entry.title.toLowerCase().includes(q) || entry.code.toLowerCase().includes(q)) {
      seen.add(entry.code)
      matches.push(entry)
    }
  }
  return matches
}
