/**
 * Unit tests for LanguageFilterControl component
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LanguageFilterControl from './LanguageFilterControl.vue'
import { useMainStore } from '@/stores/main'

describe('LanguageFilterControl', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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

  it('renders a trigger button, closed by default', () => {
    setBookLanguages(['en', 'fr'])

    const wrapper = mount(LanguageFilterControl)

    expect(wrapper.find('.language-filter__trigger').exists()).toBe(true)
    expect(wrapper.find('.language-filter__panel').exists()).toBe(false)
  })

  it('opens a scrollable panel listing "All languages" plus every book language', async () => {
    setBookLanguages(['en', 'fr', 'nl'])

    const wrapper = mount(LanguageFilterControl)
    await wrapper.find('.language-filter__trigger').trigger('click')

    expect(wrapper.find('.language-filter__panel').exists()).toBe(true)
    const texts = wrapper.findAll('.language-filter__item').map((item) => item.text())
    expect(texts).toEqual(['languageFilter.allLanguages', 'Dutch', 'English', 'French'])
  })

  it('filters the list by typing, without affecting the "All languages" option', async () => {
    setBookLanguages(['en', 'fr', 'nl'])

    const wrapper = mount(LanguageFilterControl)
    await wrapper.find('.language-filter__trigger').trigger('click')
    await wrapper.find('.language-filter__search').setValue('fr')

    const texts = wrapper.findAll('.language-filter__item').map((item) => item.text())
    expect(texts).toEqual(['languageFilter.allLanguages', 'French'])
  })

  it('resets the search query every time the panel is reopened', async () => {
    setBookLanguages(['en', 'fr'])

    const wrapper = mount(LanguageFilterControl)
    await wrapper.find('.language-filter__trigger').trigger('click')
    await wrapper.find('.language-filter__search').setValue('fr')
    await wrapper.find('.language-filter__trigger').trigger('click') // close
    await wrapper.find('.language-filter__trigger').trigger('click') // reopen

    expect(wrapper.find('.language-filter__search').element.value).toBe('')
    expect(wrapper.findAll('.language-filter__item')).toHaveLength(3)
  })

  it('selects a language, updates the store and closes the panel', async () => {
    setBookLanguages(['en', 'fr'])

    const wrapper = mount(LanguageFilterControl)
    await wrapper.find('.language-filter__trigger').trigger('click')
    await wrapper.find('.language-filter__search').setValue('french')
    await wrapper.find('.language-filter__item:not(:first-child)').trigger('click')

    expect(useMainStore().selectedLanguage).toBe('fr')
    expect(wrapper.find('.language-filter__panel').exists()).toBe(false)
  })

  it('closes on an outside click', async () => {
    setBookLanguages(['en', 'fr'])
    const wrapper = mount(LanguageFilterControl, { attachTo: document.body })

    await wrapper.find('.language-filter__trigger').trigger('click')
    expect(wrapper.find('.language-filter__panel').exists()).toBe(true)

    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.language-filter__panel').exists()).toBe(false)
    wrapper.unmount()
  })
})
