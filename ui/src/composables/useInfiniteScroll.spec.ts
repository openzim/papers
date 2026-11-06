/**
 * Unit tests for useInfiniteScroll
 * Covers resetting the displayed batch when the list it reads changes
 */

import { describe, it, expect } from 'vitest'
import { nextTick, ref } from 'vue'
import { useInfiniteScroll } from './useInfiniteScroll'

describe('useInfiniteScroll', () => {
  function setup(count: number, options?: { resetOnItemsChange?: boolean }) {
    const items = ref(Array.from({ length: count }, (_, index) => index))
    return { items, ...useInfiniteScroll(() => items.value, 10, options) }
  }

  it('shows the first batch and grows on demand', () => {
    const scroll = setup(30)

    expect(scroll.displayedItems.value).toHaveLength(10)

    scroll.loadMore()

    expect(scroll.displayedItems.value).toHaveLength(20)
    expect(scroll.hasMore.value).toBe(true)
  })

  it('resets the batch when the list it reads changes', async () => {
    const scroll = setup(30)
    scroll.loadMore()
    expect(scroll.displayedItems.value).toHaveLength(20)

    scroll.items.value = [...scroll.items.value, 30]
    await nextTick()

    expect(scroll.displayedItems.value).toHaveLength(10)
  })

  it('keeps the batch when the caller opts out of resetting', async () => {
    const scroll = setup(30, { resetOnItemsChange: false })
    scroll.loadMore()

    scroll.items.value = [...scroll.items.value, 30]
    await nextTick()

    expect(scroll.displayedItems.value).toHaveLength(20)
  })
})
