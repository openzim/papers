/**
 * Unit tests for format-utils.ts
 * Tests cover formatting functions used throughout the UI for displaying
 * author names, dates, numbers, languages, and other user-facing content.
 */

import { describe, it, expect } from 'vitest'
import {
  compareAuthorNames,
  formatAuthorLifespan,
  formatLanguages,
  formatScrapeDate,
  pluralize,
  extractUniqueValues,
  normalizeImagePath,
  normalizeZimPath
} from './format-utils'

describe('compareAuthorNames', () => {
  it('sorts by last name first', () => {
    const smith = { sortName: 'Smith', displayName: 'Zoe Smith' }
    const andrews = { sortName: 'Andrews', displayName: 'Amy Andrews' }
    expect(compareAuthorNames(andrews, smith)).toBeLessThan(0)
    expect(compareAuthorNames(smith, andrews)).toBeGreaterThan(0)
  })

  it('does not reorder compound surnames against a shorter one', () => {
    // A composite "last, first" sort key would put "Alma-Tadema" ahead of
    // "Alma" since '-' sorts before ',' - keeping sortName as the last name
    // alone avoids that.
    const alma = { sortName: 'Alma', displayName: 'Maude Alma' }
    const almaTadema = { sortName: 'Alma-Tadema', displayName: 'Laurence Alma-Tadema' }
    expect(compareAuthorNames(alma, almaTadema)).toBeLessThan(0)
  })

  it('breaks ties on the full display name when last names match', () => {
    const alice = { sortName: 'Clarke', displayName: 'Alice Clarke' }
    const bob = { sortName: 'Clarke', displayName: 'Bob Clarke' }
    expect(compareAuthorNames(alice, bob)).toBeLessThan(0)
    expect(compareAuthorNames(bob, alice)).toBeGreaterThan(0)
  })

  it('breaks ties on a disambiguating suffix embedded in the display name', () => {
    const older = { sortName: 'Smith', displayName: 'John Smith (1850-1900)' }
    const younger = { sortName: 'Smith', displayName: 'John Smith (1950-2000)' }
    expect(compareAuthorNames(older, younger)).toBeLessThan(0)
  })

  it('falls back to the full name when the sort key and tiebreak tie', () => {
    const a = { sortName: 'Clarke', displayName: 'Alice Clarke (editor)' }
    const b = { sortName: 'Clarke', displayName: 'Alice Clarke (translator)' }
    expect(compareAuthorNames(a, b)).toBeLessThan(0)
  })
})

describe('formatAuthorLifespan', () => {
  it.each([
    { birth: '1775', death: '1817', expected: '1775 - 1817', description: 'full lifespan' },
    { birth: '1950', death: null, expected: '1950 -', description: 'birth year only' },
    { birth: null, death: '2020', expected: '- 2020', description: 'death year only' },
    { birth: null, death: null, expected: '', description: 'both years null' },
    { birth: '-384', death: '-322', expected: '-384 - -322', description: 'BCE years' },
    {
      birth: 'c. 1564',
      death: '1616',
      expected: 'c. 1564 - 1616',
      description: 'approximate years'
    }
  ])('formats $description', ({ birth, death, expected }) => {
    expect(formatAuthorLifespan(birth, death)).toBe(expected)
  })
})

describe('formatLanguages', () => {
  it.each([
    { langs: [], expected: '' },
    { langs: ['en'], expected: 'English' },
    { langs: ['fr'], expected: 'French' },
    { langs: ['en', 'fr'], expected: 'English, French' },
    { langs: ['xyz'], expected: 'xyz' }
  ])('formats $langs as "$expected" with default (en) locale', ({ langs, expected }) => {
    expect(formatLanguages(langs)).toBe(expected)
  })

  it('uses uiLocale for translated names', () => {
    expect(formatLanguages(['en'], { uiLocale: 'sk' })).toBe('angličtina')
    expect(formatLanguages(['de'], { uiLocale: 'sk' })).toBe('nemčina')
  })

  it('falls back to English when locale has no CLDR data', () => {
    expect(formatLanguages(['en'], { uiLocale: 'zzz' })).toBe('English')
  })
})

describe('formatScrapeDate', () => {
  it('formats an ISO date-only string in the given locale', () => {
    expect(formatScrapeDate('2026-09-23', 'en')).toBe('Sep 23, 2026')
  })

  it('does not shift the day across timezones (no UTC parsing)', () => {
    const formatted = formatScrapeDate('2026-01-01', 'en')
    expect(formatted).toContain('Jan 1')
  })

  it('returns the raw input when it cannot be parsed', () => {
    expect(formatScrapeDate('not-a-date', 'en')).toBe('not-a-date')
  })
})

describe('pluralize', () => {
  it.each([
    { count: 1, word: 'book', plural: undefined, expected: 'book' },
    { count: 1.0, word: 'book', plural: undefined, expected: 'book' },
    { count: 0, word: 'book', plural: undefined, expected: 'books' },
    { count: 2, word: 'book', plural: undefined, expected: 'books' },
    { count: -1, word: 'book', plural: undefined, expected: 'books' },
    { count: 1.5, word: 'book', plural: undefined, expected: 'books' },
    { count: 1, word: 'child', plural: 'children', expected: 'child' },
    { count: 2, word: 'child', plural: 'children', expected: 'children' },
    { count: 5, word: 'person', plural: 'people', expected: 'people' }
  ])('returns "$expected" for $count $word', ({ count, word, plural, expected }) => {
    expect(pluralize(count, word, plural)).toBe(expected)
  })
})

describe('extractUniqueValues', () => {
  it.each([
    {
      items: [],
      expected: [],
      description: 'empty array'
    },
    {
      items: [{ values: [] }, { values: ['a'] }, { values: [] }],
      expected: ['a'],
      description: 'items with empty arrays'
    },
    {
      items: [
        { values: ['fiction', 'classic'] },
        { values: ['fiction', 'modern'] },
        { values: ['classic'] }
      ],
      expected: ['classic', 'fiction', 'modern'],
      description: 'deduplication and sorting'
    },
    {
      items: [{ values: ['Zebra', 'apple', 'Mango'] }],
      expected: ['Mango', 'Zebra', 'apple'],
      description: 'case-sensitive sorting'
    }
  ])('handles $description', ({ items, expected }) => {
    expect(extractUniqueValues(items, (item) => item.values)).toEqual(expected)
  })
})

describe('normalizeImagePath', () => {
  it.each([
    { input: 'image.jpg', expected: './image.jpg', description: 'simple filename' },
    { input: 'path/to/image.png', expected: './path/to/image.png', description: 'path' },
    { input: './image.jpg', expected: './image.jpg', description: 'already prefixed' },
    { input: '', expected: './', description: 'empty string' },
    {
      input: '/absolute/path.jpg',
      expected: '/absolute/path.jpg',
      description: 'root-relative path'
    },
    {
      input: '//cdn.example.com/image.jpg',
      expected: '//cdn.example.com/image.jpg',
      description: 'protocol-relative URL'
    },
    {
      input: 'https://example.com/image.jpg',
      expected: 'https://example.com/image.jpg',
      description: 'absolute URL'
    },
    { input: '../image.jpg', expected: './../image.jpg', description: 'relative parent path' }
  ])('handles $description: "$input" -> "$expected"', ({ input, expected }) => {
    expect(normalizeImagePath(input)).toBe(expected)
  })
})

describe('normalizeZimPath', () => {
  it.each([
    {
      input: 'Evidence: Jury Impeachment.108.pdf',
      expected: './Evidence%3A%20Jury%20Impeachment.108.pdf',
      description: 'encodes a colon and spaces'
    },
    { input: 'a#b.pdf', expected: './a%23b.pdf', description: 'encodes a fragment marker' },
    { input: 'a?b.pdf', expected: './a%3Fb.pdf', description: 'encodes a query marker' },
    { input: '100%.pdf', expected: './100%25.pdf', description: 'encodes a literal percent' },
    {
      input: 'folder/sub/book.epub',
      expected: './folder/sub/book.epub',
      description: 'keeps a safe multi-segment path relative'
    },
    { input: './book.epub', expected: './book.epub', description: 'keeps the prefix' },
    {
      input: '../book.epub',
      expected: './../book.epub',
      description: 'keeps the parent segment'
    },
    {
      input: 'https://example.com/a?b=1#c',
      expected: 'https://example.com/a?b=1#c',
      description: 'leaves an absolute URL untouched'
    },
    {
      input: '//cdn.example.com/book.epub',
      expected: '//cdn.example.com/book.epub',
      description: 'leaves a protocol-relative URL untouched'
    }
  ])('handles $description: "$input" -> "$expected"', ({ input, expected }) => {
    expect(normalizeZimPath(input)).toBe(expected)
  })

  it('escapes the query marker of a title ending in a question mark', () => {
    const title = 'ਮੈਂ ਨਾਸਤਿਕ ਕਿਉਂ ਹਾਂ?.pa_1d51d0d1.epub'

    expect(normalizeZimPath(title)).toBe(`./${encodeURIComponent(title)}`)
    expect(normalizeZimPath(title)).toContain('%3F')
    expect(normalizeZimPath(title)).not.toContain('?')
  })
})
