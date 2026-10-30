/**
 * Unit tests for BookLicense component
 */

import { describe, it, expect, afterEach } from 'vitest'
import { config, enableAutoUnmount, mount } from '@vue/test-utils'
import type { Composer } from 'vue-i18n'
import BookLicense from './BookLicense.vue'

function render(props: { license: string; licenseId?: string | null }) {
  return mount(BookLicense, { props })
}

describe('BookLicense', () => {
  // Components of earlier tests must not re-render when the locale changes
  enableAutoUnmount(afterEach)

  it('shows a localized name and a link for a versioned Creative Commons license', () => {
    const wrapper = render({
      license: 'http://creativecommons.org/licenses/by-sa/3.0',
      licenseId: 'CC-BY-SA-3.0'
    })

    const link = wrapper.get('a')
    expect(link.text()).toBe('Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)')
    expect(link.attributes('href')).toBe('https://creativecommons.org/licenses/by-sa/3.0/')
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toBe('noopener noreferrer')
    expect(wrapper.text()).not.toContain('http://')
  })

  it('combines every element of the license', () => {
    const wrapper = render({ license: '', licenseId: 'CC-BY-NC-ND-4.0' })

    expect(wrapper.text()).toBe(
      'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 (CC BY-NC-ND 4.0)'
    )
  })

  it('shows an unversioned license without a link', () => {
    const wrapper = render({
      license: 'Attribution-NonCommercial-ShareAlike',
      licenseId: 'CC-BY-NC-SA'
    })

    expect(wrapper.text()).toBe(
      'Creative Commons Attribution-NonCommercial-ShareAlike (CC BY-NC-SA)'
    )
    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('shows CC0 with a link', () => {
    const wrapper = render({ license: 'CC0', licenseId: 'CC0-1.0' })

    expect(wrapper.get('a').text()).toBe('CC0 1.0 Universal')
    expect(wrapper.get('a').attributes('href')).toBe(
      'https://creativecommons.org/publicdomain/zero/1.0/'
    )
  })

  it('falls back to the source text without a trailing period', () => {
    const wrapper = render({ license: 'Public domain in the USA.', licenseId: null })

    expect(wrapper.text()).toBe('Public domain in the USA')
    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('falls back to the source text when the identifier is not recognized', () => {
    const wrapper = render({ license: 'Some other license', licenseId: 'LicenseRef-other' })

    expect(wrapper.text()).toBe('Some other license')
  })

  describe('in another language', () => {
    // The i18n instance installed for every test by vitest.setup.ts
    const { global: i18n } = config.global.plugins.find(
      (plugin) => typeof plugin === 'object' && plugin !== null && 'global' in plugin
    ) as unknown as { global: Composer }

    afterEach(() => {
      i18n.locale.value = 'en'
    })

    it('builds the name from the translated messages', async () => {
      i18n.setLocaleMessage('xx', {
        licenses: {
          termBy: 'Namensnennung',
          termSa: 'Weitergabe',
          termSeparator: ' - ',
          ccName: 'Lizenz {terms} {version}'
        }
      })
      i18n.locale.value = 'xx'

      const wrapper = render({ license: '', licenseId: 'CC-BY-SA-4.0' })

      expect(wrapper.text()).toBe('Lizenz Namensnennung - Weitergabe 4.0 (CC BY-SA 4.0)')
    })
  })
})
