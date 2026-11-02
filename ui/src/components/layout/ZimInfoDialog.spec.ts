/**
 * Unit tests for ZimInfoDialog component
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ZimInfoDialog from './ZimInfoDialog.vue'
import { useMainStore } from '@/stores/main'
import type { ZimContentInfo } from '@/types/Config'

describe('ZimInfoDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  function setContentInfo(contentInfo: ZimContentInfo) {
    useMainStore().config = {
      title: 'Test',
      description: null,
      zimName: 'test',
      bookLanguages: ['en'],
      source: { slug: 'test', name: 'Test', description: 'Test' },
      theme: { formatIcons: {}, routeLabels: {}, collectionIconStyle: 'classification' },
      features: { epubReader: true, pdfReader: true, noscriptFallback: true },
      contentInfo
    }
  }

  function mountOpen() {
    return mount(ZimInfoDialog, {
      props: { modelValue: true },
      attachTo: document.body
    })
  }

  it('shows "All" for every dimension that was not filtered', () => {
    setContentInfo({
      source: 'Project Gutenberg',
      collections: null,
      books: null,
      languages: null,
      formats: null,
      dateScraped: '2026-09-23'
    })

    mountOpen()

    const rows = document.body.querySelectorAll('.zim-info-dialog__row dd')
    const allCount = Array.from(rows).filter((row) => row.textContent?.trim() === 'All').length
    expect(allCount).toBe(4)
    expect(document.body.textContent).toContain('Project Gutenberg')
  })

  it('renders a single filtered value as plain text', () => {
    setContentInfo({
      source: 'Project Gutenberg',
      collections: ['P'],
      books: null,
      languages: ['en'],
      formats: null,
      dateScraped: '2026-09-23'
    })

    mountOpen()

    expect(document.body.querySelectorAll('.zim-info-dialog__bullets')).toHaveLength(0)
    expect(document.body.textContent).toContain('P')
  })

  it('renders multiple filtered values as a bullet list', () => {
    setContentInfo({
      source: 'Project Gutenberg',
      collections: ['P', 'PR'],
      books: null,
      languages: null,
      formats: null,
      dateScraped: '2026-09-23'
    })

    mountOpen()

    const bullets = document.body.querySelectorAll('.zim-info-dialog__bullets li')
    expect(bullets).toHaveLength(2)
  })

  it('always renders formats as a comma-separated list, never bullets', () => {
    setContentInfo({
      source: 'Project Gutenberg',
      collections: null,
      books: null,
      languages: null,
      formats: ['epub', 'pdf'],
      dateScraped: '2026-09-23'
    })

    mountOpen()

    expect(document.body.querySelectorAll('.zim-info-dialog__bullets')).toHaveLength(0)
    expect(document.body.textContent).toContain('ePUB, PDF')
  })

  it('shows book titles only, without author names', () => {
    setContentInfo({
      source: 'Project Gutenberg',
      collections: null,
      books: ['Bleak House', 'Emma'],
      languages: null,
      formats: null,
      dateScraped: '2026-09-23'
    })

    mountOpen()

    const bullets = Array.from(document.body.querySelectorAll('.zim-info-dialog__bullets li'))
    expect(bullets.map((li) => li.textContent)).toEqual(['Bleak House', 'Emma'])
  })

  it('pluralizes labels on the number of values, plural when all are included', () => {
    setContentInfo({
      source: 'Project Gutenberg',
      collections: ['P'],
      books: ['Bleak House', 'Emma'],
      languages: null,
      formats: ['epub'],
      dateScraped: '2026-09-23'
    })

    mountOpen()

    const labels = Array.from(document.body.querySelectorAll('.zim-info-dialog__row dt')).map(
      (dt) => dt.textContent?.trim()
    )
    expect(labels).toEqual(['Source', 'Collection', 'Books', 'Languages', 'Format', 'Date scraped'])
  })
})
