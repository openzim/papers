/**
 * Component tests for CollectionSidebar
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CollectionSidebar from './CollectionSidebar.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key: string) => key })
}))

vi.mock('@/constants/theme', () => ({
  TYPOGRAPHY: {
    FONT_FAMILY: 'sans-serif',
    BODY_WEIGHT: 400,
    BODY_SIZE: '1rem',
    SMALL_SIZE: '0.875rem'
  }
}))

vi.mock('@/utils/collection-names', () => ({
  getCollectionLabel: (id: string) => id
}))

describe('CollectionSidebar', () => {
  it('renders collection name and book count correctly without underline regression (issue #24)', () => {
    const wrapper = mount(CollectionSidebar, {
      props: {
        collections: [{ id: 'history', name: 'History', bookCount: 2 }],
        activeId: 'history',
        totalBooks: 10
      },
      global: {
        stubs: {
          ClassificationIcon: true,
          SubjectCollectionIcon: true
        }
      }
    })

    const buttons = wrapper.findAll('.collection-sidebar__btn')
    expect(buttons.length).toBe(2)

    // 1. Check 'All Collections' button
    const allBtn = buttons[0]
    const allCountSpan = allBtn.find('.collection-sidebar__count')
    expect(allCountSpan.exists()).toBe(true)

    // The space is handled by CSS margin-inline-start, so the textContent is just the count
    expect(allCountSpan.element.textContent).toBe('(10)')

    const allParentSpan = allBtn.findAll('span')[0]
    const allChildNodes = Array.from(allParentSpan.element.childNodes)
    const allCountIndex = allChildNodes.findIndex((node) => node === allCountSpan.element)

    const allPrevNode = allChildNodes[allCountIndex - 1]
    expect(allPrevNode.nodeType).toBe(Node.TEXT_NODE)
    // Must NOT have a trailing space (which would be underlined by the active button)
    expect(allPrevNode.textContent).toBe('collection.allCollections')

    // 2. Check individual collection button
    const historyBtn = buttons[1]
    // The text span is inside the button (icon is first, then the span)
    const historyCountSpan = historyBtn.find('.collection-sidebar__count')
    expect(historyCountSpan.exists()).toBe(true)

    // The space is handled by CSS margin-inline-start, so the textContent is just the count
    expect(historyCountSpan.element.textContent).toBe('(2)')

    const historyParentSpan = historyBtn.findAll('span')[0]
    const historyChildNodes = Array.from(historyParentSpan.element.childNodes)
    const historyCountIndex = historyChildNodes.findIndex(
      (node) => node === historyCountSpan.element
    )

    const historyPrevNode = historyChildNodes[historyCountIndex - 1]
    expect(historyPrevNode.nodeType).toBe(Node.TEXT_NODE)
    // Must NOT have a trailing space
    expect(historyPrevNode.textContent).toBe('History')
  })
})
