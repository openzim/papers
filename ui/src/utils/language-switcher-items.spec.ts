import { describe, it, expect } from 'vitest'
import { buildLanguageSwitcherItems, isDivider, type LanguageItem } from './language-switcher-items'
import { getPinnedLanguages } from '@/plugins/i18n'

function codesOf(entries: ReturnType<typeof buildLanguageSwitcherItems>) {
  return entries.map((entry) => (isDivider(entry) ? '---' : entry.code))
}

describe('buildLanguageSwitcherItems', () => {
  it('pins the ZIM language first for a single-language ZIM, followed by a divider', () => {
    const items = buildLanguageSwitcherItems(['de'])

    expect(codesOf(items)).toContain('de')
    expect(items.some(isDivider)).toBe(true)
    // the pinned entry and its normal-position entry both resolve to "de"
    expect(codesOf(items).filter((code) => code === 'de').length).toBe(2)
  })

  it('does not pin a ZIM language for a multi-language ZIM', () => {
    const expectedPinned = getPinnedLanguages(['de', 'fr']).map((lang) => lang.code)
    const items = buildLanguageSwitcherItems(['de', 'fr'])
    const dividerIndex = items.findIndex(isDivider)
    const pinnedSection = dividerIndex === -1 ? [] : items.slice(0, dividerIndex)

    expect((pinnedSection as LanguageItem[]).map((entry) => entry.code)).toEqual(expectedPinned)
    expect(expectedPinned).not.toContain('de')
    expect(expectedPinned).not.toContain('fr')
  })

  it('pins exactly what getPinnedLanguages reports, nothing more', () => {
    const expectedPinned = getPinnedLanguages([])
    const items = buildLanguageSwitcherItems([])
    const dividerIndex = items.findIndex(isDivider)
    const pinnedSection = dividerIndex === -1 ? [] : items.slice(0, dividerIndex)

    expect(pinnedSection.some(isDivider)).toBe(false)
    expect((pinnedSection as LanguageItem[]).map((entry) => entry.code)).toEqual(
      expectedPinned.map((lang) => lang.code)
    )
    expect(items.some(isDivider)).toBe(expectedPinned.length > 0)
  })

  function fullListOnly(items: ReturnType<typeof buildLanguageSwitcherItems>) {
    const dividerIndex = items.findIndex(isDivider)
    return (dividerIndex === -1 ? items : items.slice(dividerIndex + 1)) as LanguageItem[]
  }

  it('sorts the full list by native display name, not by code', () => {
    const titles = fullListOnly(buildLanguageSwitcherItems(['de'])).map((entry) =>
      entry.title.toLowerCase()
    )
    const sorted = [...titles].sort((a, b) => a.localeCompare(b))

    expect(titles).toEqual(sorted)
  })

  it('formats "native - English" when the names differ, and just the name when they match', () => {
    const byCode = Object.fromEntries(
      fullListOnly(buildLanguageSwitcherItems(['de'])).map((e) => [e.code, e])
    )

    expect(byCode['en']!.title).toBe('English')
    expect(byCode['de']!.title).toBe('Deutsch - German')
    expect(byCode['fr']!.title).toBe('français - French')
  })
})
