/* global Buffer, console */
/**
 * Extracts translated language names from CLDR data for use at runtime.
 * Only includes language codes used by Project Gutenberg and UI locales
 * that have CLDR translations available. This keeps the bundle minimal (~52KB)
 * instead of shipping the full 25MB CLDR package.
 *
 * Run: node scripts/generate-language-names.js
 */

import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const __dirname = dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)

const cldrBase = dirname(require.resolve('cldr-localenames-full/package.json'))

// Language codes used in Project Gutenberg books.
const GUTENBERG_LANGUAGE_CODES = [
  'af',
  'ale',
  'ang',
  'ar',
  'arp',
  'bg',
  'bgs',
  'bo',
  'br',
  'brx',
  'ca',
  'ceb',
  'cs',
  'csb',
  'cy',
  'da',
  'de',
  'el',
  'en',
  'enm',
  'eo',
  'es',
  'et',
  'fa',
  'fi',
  'fr',
  'fur',
  'fy',
  'ga',
  'gl',
  'gla',
  'grc',
  'hai',
  'he',
  'hu',
  'ia',
  'ilo',
  'is',
  'it',
  'iu',
  'ja',
  'kha',
  'kld',
  'ko',
  'la',
  'lt',
  'mi',
  'myn',
  'nah',
  'nai',
  'nap',
  'nav',
  'nl',
  'no',
  'oc',
  'oji',
  'pl',
  'pt',
  'rmq',
  'ro',
  'ru',
  'sa',
  'sco',
  'sl',
  'sr',
  'sv',
  'te',
  'tl',
  'yi',
  'zh'
]

// Gutenberg uses ISO 639-3 codes where CLDR has an ISO 639-1 key.
const GUTENBERG_CODE_TO_CLDR = {
  gla: 'gd', // Scottish Gaelic
  nav: 'nv', // Navajo
  oji: 'oj' // Ojibwa
}

// papers' own UI interface locale codes use IETF-ish tags that sometimes
// differ from the CLDR key for the same language/script/region.
const UI_LOCALE_CODE_TO_CLDR = {
  'pt-br': 'pt-BR',
  'zh-hans': 'zh-Hans',
  'zh-hant': 'zh-Hant'
}

// Each UI locale has one file; source-specific messages are top-level namespaces.
const localesDir = resolve(__dirname, '../../locales')
const UI_LOCALES = readdirSync(localesDir)
  .filter((f) => f.endsWith('.json') && f !== 'qqq.json')
  .map((f) => f.replace('.json', ''))

// A locale only shows up in the language switcher once its translation is
// substantially complete - a 1%-translated locale offered in the switcher is
// worse than not offering it at all, since nearly everything would silently
// fall back to English anyway. Completeness is counted per source
// (`common` + that source's own namespace, e.g. `gutenberg`), not as one
// combined count across `common` + every source: otherwise adding a new
// source with its own batch of untranslated strings would lower every
// existing language's percentage and could silently drop languages from
// ZIMs of unrelated, already-translated sources. See
// https://github.com/openzim/papers/issues/113
const COMPLETENESS_THRESHOLD = 0.8

// Mirrors `get_leaf_keys` in scraper/src/papers2zim/scripts/validate_i18n.py:
// recursively collects leaf keys, treating a plural message (an object keyed
// by CLDR plural category, e.g. `{"one": "Book", "other": "Books"}`) as a
// single leaf rather than descending into its forms.
const PLURAL_CATEGORIES = new Set(['zero', 'one', 'two', 'few', 'many', 'other'])

function isPluralMessage(value) {
  return (
    !!value &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    Object.keys(value).length > 0 &&
    Object.keys(value).every((key) => PLURAL_CATEGORIES.has(key)) &&
    Object.values(value).every((form) => typeof form === 'string')
  )
}

function getLeafKeys(data, prefix = '') {
  const result = new Set()
  for (const [key, value] of Object.entries(data)) {
    if (key === '@metadata') continue
    const fullKey = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value) && !isPluralMessage(value)) {
      for (const leafKey of getLeafKeys(value, fullKey)) result.add(leafKey)
    } else {
      result.add(fullKey)
    }
  }
  return result
}

const enData = JSON.parse(readFileSync(resolve(localesDir, 'en.json'), 'utf-8'))
const commonEnKeys = getLeafKeys(enData.common || {})

// Source namespaces are en.json's top-level keys besides `common` and its
// own metadata fields - e.g. `gutenberg`, `wikisource`.
const SOURCE_NAMESPACES = Object.keys(enData).filter(
  (key) =>
    !['@metadata', 'language', 'isocode', 'common'].includes(key) &&
    enData[key] &&
    typeof enData[key] === 'object' &&
    !Array.isArray(enData[key])
)

// Locale codes above the completeness threshold, per source namespace - used
// at runtime to only offer a language in the switcher for ZIMs of sources
// it's actually translated for.
const UI_LOCALES_BY_SOURCE = {}
for (const source of SOURCE_NAMESPACES) {
  const requiredKeys = new Set([...commonEnKeys, ...getLeafKeys(enData[source] || {})])
  UI_LOCALES_BY_SOURCE[source] = UI_LOCALES.filter((locale) => {
    if (requiredKeys.size === 0) return false
    const data = JSON.parse(readFileSync(resolve(localesDir, `${locale}.json`), 'utf-8'))
    const translatedKeys = new Set([
      ...getLeafKeys(data.common || {}),
      ...getLeafKeys(data[source] || {})
    ])
    const translatedCount = [...requiredKeys].filter((key) => translatedKeys.has(key)).length
    return translatedCount / requiredKeys.size >= COMPLETENESS_THRESHOLD
  })
}

// Union across sources: used for CLDR language-name extraction below, which
// isn't source-specific - a locale eligible for at least one source is worth
// having native/English language names for.
const UI_INTERFACE_LOCALES = [...new Set(Object.values(UI_LOCALES_BY_SOURCE).flat())]

// Source code -> CLDR code, merging Gutenberg's book-language codes (for
// book-language badges) with papers' own UI interface locale codes (for the
// language switcher's native + English labels), each resolved through its
// own code-to-CLDR mapping.
const requestedCodes = new Map()
for (const code of GUTENBERG_LANGUAGE_CODES) {
  requestedCodes.set(code, GUTENBERG_CODE_TO_CLDR[code] || code)
}
for (const code of UI_INTERFACE_LOCALES) {
  if (!requestedCodes.has(code)) {
    requestedCodes.set(code, UI_LOCALE_CODE_TO_CLDR[code] || code)
  }
}

const result = {}

for (const locale of UI_INTERFACE_LOCALES) {
  const filePath = resolve(cldrBase, 'main', locale, 'languages.json')
  if (!existsSync(filePath)) continue

  const data = JSON.parse(readFileSync(filePath, 'utf-8'))
  const cldrKey = Object.keys(data.main)[0]
  const languages = data.main[cldrKey].localeDisplayNames.languages

  const localeData = {}
  for (const [code, cldrCode] of requestedCodes) {
    if (languages[cldrCode]) {
      localeData[code] = languages[cldrCode]
    }
  }

  if (Object.keys(localeData).length > 0) {
    result[locale] = localeData
  }
}

const outPath = resolve(__dirname, '../src/generated/language-names.json')
mkdirSync(dirname(outPath), { recursive: true })
writeFileSync(outPath, JSON.stringify(result) + '\n')

const uiLocalesOutPath = resolve(__dirname, '../src/generated/ui-locales.json')
writeFileSync(uiLocalesOutPath, JSON.stringify(UI_LOCALES_BY_SOURCE) + '\n')

const size = Buffer.byteLength(JSON.stringify(result))
const localeCount = Object.keys(result).length
console.log(`Generated ${outPath}`)
console.log(`  ${localeCount} locales, ${size} bytes (${(size / 1024).toFixed(1)} KB)`)
console.log(`Generated ${uiLocalesOutPath}`)
for (const source of SOURCE_NAMESPACES) {
  console.log(`  ${source}: ${UI_LOCALES_BY_SOURCE[source].length} interface locales`)
}
