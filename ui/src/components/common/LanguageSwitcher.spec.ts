/**
 * Unit tests for LanguageSwitcher component
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LanguageSwitcher from './LanguageSwitcher.vue'
import { useMainStore } from '@/stores/main'
import { getCurrentLocale, setCurrentLocale, supportedLanguages } from '@/plugins/i18n'

describe('LanguageSwitcher', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    await setCurrentLocale(
      supportedLanguages.find((lang) => lang.code === 'en')!,
      false
    )
  })

  function setBookLanguages(bookLanguages: string[]) {
    useMainStore().config = {
      title: 'Test',
      description: null,
      zimName: 'test',
      bookLanguages,
      source: { slug: 'test', name: 'Test', description: 'Test' },
      theme: { formatIcons: {}, routeLabels: {}, collectionIconStyle: 'classification' },
      features: { epubReader: true, pdfReader: true, noscriptFallback: true },
      contentInfo: {
        source: 'Test',
        collections: null,
        books: null,
        languages: null,
        formats: null,
        dateScraped: '2026-01-01'
      }
    }
  }

  it('renders a translate-icon trigger button, closed by default', () => {
    setBookLanguages(['en', 'fr'])

    const wrapper = mount(LanguageSwitcher)

    const trigger = wrapper.find('.language-switcher__trigger')
    expect(trigger.exists()).toBe(true)
    expect(trigger.attributes('aria-label')).toBe('common.changeInterfaceLanguage')
    expect(trigger.attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('.language-switcher__menu').exists()).toBe(false)
  })

  it('opens the menu with a populated, pinned-first list', async () => {
    setBookLanguages(['de'])

    const wrapper = mount(LanguageSwitcher)
    await wrapper.find('.language-switcher__trigger').trigger('click')

    expect(wrapper.find('.language-switcher__trigger').attributes('aria-expanded')).toBe('true')
    const texts = wrapper.findAll('.language-switcher__item').map((item) => item.text())
    // every supported language once, plus the pinned duplicates
    expect(texts.length).toBeGreaterThan(supportedLanguages.length)
    // "Deutsch - German" (the ZIM's single language) is pinned, alongside
    // whatever the test environment's browser language resolves to, and
    // still appears again further down in its normal sorted position
    expect(texts.indexOf('Deutsch - German')).toBeLessThan(5)
    expect(texts.filter((title) => title === 'Deutsch - German')).toHaveLength(2)
    expect(wrapper.find('.language-switcher__divider').exists()).toBe(true)
  })

  it('toggles closed when the trigger is clicked again', async () => {
    setBookLanguages(['en', 'fr'])
    const wrapper = mount(LanguageSwitcher)

    await wrapper.find('.language-switcher__trigger').trigger('click')
    expect(wrapper.find('.language-switcher__menu').exists()).toBe(true)

    await wrapper.find('.language-switcher__trigger').trigger('click')
    expect(wrapper.find('.language-switcher__menu').exists()).toBe(false)
  })

  it('closes on an outside click', async () => {
    setBookLanguages(['en', 'fr'])
    const wrapper = mount(LanguageSwitcher, { attachTo: document.body })

    await wrapper.find('.language-switcher__trigger').trigger('click')
    expect(wrapper.find('.language-switcher__menu').exists()).toBe(true)

    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.language-switcher__menu').exists()).toBe(false)
    wrapper.unmount()
  })

  it('does not close when clicking inside the menu (e.g. the search field)', async () => {
    setBookLanguages(['en', 'fr'])
    const wrapper = mount(LanguageSwitcher, { attachTo: document.body })

    await wrapper.find('.language-switcher__trigger').trigger('click')
    await wrapper.find('.language-switcher__search').trigger('click')

    expect(wrapper.find('.language-switcher__menu').exists()).toBe(true)
    wrapper.unmount()
  })

  it('filters the list by native or English name, without duplicates', async () => {
    setBookLanguages(['en', 'fr'])
    const wrapper = mount(LanguageSwitcher)
    await wrapper.find('.language-switcher__trigger').trigger('click')

    await wrapper.find('.language-switcher__search').setValue('german')

    const texts = wrapper.findAll('.language-switcher__item').map((item) => item.text())
    expect(texts).toEqual(['Deutsch - German'])
    expect(wrapper.find('.language-switcher__divider').exists()).toBe(false)
  })

  it('switches the interface locale and closes when an item is selected', async () => {
    setBookLanguages(['en', 'fr'])
    const wrapper = mount(LanguageSwitcher)
    await wrapper.find('.language-switcher__trigger').trigger('click')
    await wrapper.find('.language-switcher__search').setValue('fran')

    await wrapper.find('.language-switcher__item').trigger('click')

    expect(wrapper.find('.language-switcher__menu').exists()).toBe(false)
    // `setCurrentLocale` loads the target locale's messages via a real
    // dynamic import, which outlasts a plain `nextTick`
    await vi.waitFor(() => expect(getCurrentLocale()).toBe('fr'))
  })
})
