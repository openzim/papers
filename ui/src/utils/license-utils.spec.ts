import { describe, it, expect } from 'vitest'
import { parseLicenseId } from './license-utils'

describe('parseLicenseId', () => {
  it('parses a versioned Creative Commons license', () => {
    expect(parseLicenseId('CC-BY-SA-3.0')).toEqual({
      kind: 'cc',
      terms: ['by', 'sa'],
      version: '3.0',
      code: 'CC BY-SA 3.0',
      url: 'https://creativecommons.org/licenses/by-sa/3.0/'
    })
  })

  it.each([
    ['CC-BY-4.0', ['by'], 'CC BY 4.0'],
    ['CC-BY-NC-4.0', ['by', 'nc'], 'CC BY-NC 4.0'],
    ['CC-BY-NC-SA-2.5', ['by', 'nc', 'sa'], 'CC BY-NC-SA 2.5'],
    ['CC-BY-NC-ND-4.0', ['by', 'nc', 'nd'], 'CC BY-NC-ND 4.0'],
    ['CC-BY-ND-3.0', ['by', 'nd'], 'CC BY-ND 3.0']
  ])('reads the elements of %s', (id, terms, code) => {
    const parsed = parseLicenseId(id)
    expect(parsed).toMatchObject({ kind: 'cc', terms, code })
  })

  it('parses an unversioned license without a link', () => {
    expect(parseLicenseId('CC-BY-NC-SA')).toEqual({
      kind: 'cc',
      terms: ['by', 'nc', 'sa'],
      version: null,
      code: 'CC BY-NC-SA',
      url: null
    })
  })

  it('parses CC0', () => {
    expect(parseLicenseId('CC0-1.0')).toEqual({
      kind: 'cc0',
      code: 'CC0 1.0',
      url: 'https://creativecommons.org/publicdomain/zero/1.0/'
    })
  })

  it.each([
    null,
    undefined,
    '',
    'Public domain in the USA.',
    'http://creativecommons.org/licenses/by-sa/3.0',
    'CC-BY-ND-NC-4.0',
    'CC-BY-SA-3',
    'cc-by-sa-3.0',
    'GFDL-1.3'
  ])('returns null for %s', (id) => {
    expect(parseLicenseId(id)).toBeNull()
  })
})
