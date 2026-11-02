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

// Some locale files exist only to supply a source's `metadata_defaults`
// (ZIM title/description) in that language, with no `common` namespace -
// i.e. no actual interface translation. Selecting one of those as the UI
// language would be a no-op (everything falls back to English), so only
// locales with real translated UI strings are treated as interface locales:
// both as language-switcher options and as targets to generate book-language
// name translations for (translating book languages into an interface
// language nobody can select is pointless).
const UI_INTERFACE_LOCALES = UI_LOCALES.filter((locale) => {
  const data = JSON.parse(readFileSync(resolve(localesDir, `${locale}.json`), 'utf-8'))
  return !!(data.common && Object.keys(data.common).length > 0)
})

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
writeFileSync(uiLocalesOutPath, JSON.stringify(UI_INTERFACE_LOCALES) + '\n')

const size = Buffer.byteLength(JSON.stringify(result))
const localeCount = Object.keys(result).length
console.log(`Generated ${outPath}`)
console.log(`  ${localeCount} locales, ${size} bytes (${(size / 1024).toFixed(1)} KB)`)
console.log(`Generated ${uiLocalesOutPath}`)
console.log(`  ${UI_INTERFACE_LOCALES.length} interface locales`)
