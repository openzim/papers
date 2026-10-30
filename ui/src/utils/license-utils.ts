/**
 * Creative Commons license identifiers, as emitted by the scraper in a book's
 * `licenseId` (e.g. `CC-BY-SA-3.0`, `CC-BY-NC-SA`, `CC0-1.0`). Versioned
 * identifiers follow SPDX; unversioned ones come from sources that do not say
 * which version applies and have no canonical page.
 */

export type LicenseTerm = 'by' | 'nc' | 'nd' | 'sa'

export type ParsedLicense =
  | {
      kind: 'cc'
      /** License elements in display order, e.g. `['by', 'nc', 'sa']` */
      terms: LicenseTerm[]
      version: string | null
      /** Short code, e.g. `CC BY-SA 3.0` */
      code: string
      /** Canonical page of the license, when its version is known */
      url: string | null
    }
  | { kind: 'cc0'; code: string; url: string }

const CC_ID = /^CC-(BY(?:-NC)?(?:-ND|-SA)?)(?:-(\d\.\d))?$/
const CC0_ID = 'CC0-1.0'

/**
 * Parse a license identifier. Returns `null` for anything that is not a
 * Creative Commons identifier, so callers can show the source's own text.
 */
export function parseLicenseId(licenseId: string | null | undefined): ParsedLicense | null {
  if (!licenseId) return null
  if (licenseId === CC0_ID) {
    return {
      kind: 'cc0',
      code: 'CC0 1.0',
      url: 'https://creativecommons.org/publicdomain/zero/1.0/'
    }
  }
  const match = CC_ID.exec(licenseId)
  if (!match) return null
  const [, elements = '', version] = match
  return {
    kind: 'cc',
    terms: elements.toLowerCase().split('-') as LicenseTerm[],
    version: version ?? null,
    code: version ? `CC ${elements} ${version}` : `CC ${elements}`,
    url: version
      ? `https://creativecommons.org/licenses/${elements.toLowerCase()}/${version}/`
      : null
  }
}
