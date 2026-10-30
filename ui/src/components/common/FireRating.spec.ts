/**
 * Unit tests for FireRating component
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import FireRating from './FireRating.vue'
import { useMainStore } from '@/stores/main'

describe('FireRating', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function setConfigPopularity(popularity: boolean) {
    useMainStore().config = {
      title: 'Test',
      description: null,
      zimName: 'test',
      bookLanguages: ['en'],
      source: { slug: 'test', name: 'Test', description: 'Test' },
      theme: { formatIcons: {}, routeLabels: {}, collectionIconStyle: 'classification' },
      features: {
        epubReader: true,
        pdfReader: true,
        noscriptFallback: true,
        hasPopularity: popularity
      },
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

  it('renders three flames with the given rating', () => {
    const wrapper = mount(FireRating, { props: { flames: 2 } })

    const icons = wrapper.findAll('.flame-icon')
    expect(icons).toHaveLength(3)
    expect(icons.filter((i) => !i.classes('flame-icon--dim'))).toHaveLength(2)
  })

  it('renders when the source has popularity', () => {
    setConfigPopularity(true)

    const wrapper = mount(FireRating, { props: { flames: 3 } })

    expect(wrapper.find('.fire-rating').exists()).toBe(true)
  })

  it('renders nothing when the source has no popularity', () => {
    setConfigPopularity(false)

    const wrapper = mount(FireRating, { props: { flames: 3 } })

    expect(wrapper.find('.fire-rating').exists()).toBe(false)
  })
})
