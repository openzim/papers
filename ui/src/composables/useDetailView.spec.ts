/**
 * Unit tests for useDetailView
 * Covers rewriting an address bar that names a book by its source id to the
 * canonical slug the detail data carries.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useDetailView } from './useDetailView'

const mockRoute = {
  name: 'book-detail',
  params: { id: '42' } as Record<string, string>,
  meta: {}
}
const mockReplace = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => ({ replace: mockReplace })
}))

interface Detail {
  id?: string
  title?: string
}

function mountView(fetchFn: (id: string) => Promise<Detail>) {
  return mount(
    defineComponent({
      setup() {
        useDetailView(fetchFn, 'id')
        return () => h('div')
      }
    })
  )
}

describe('useDetailView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRoute.params = { id: '42' }
    mockReplace.mockReset()
  })

  it('replaces a source id in the route with the slug of the loaded book', async () => {
    mountView(async () => ({ id: 'bleak-house', title: 'Bleak House' }))
    await flushPromises()

    expect(mockReplace).toHaveBeenCalledWith({
      name: 'book-detail',
      params: { id: 'bleak-house' }
    })
  })

  it('keeps the route when it already names the slug', async () => {
    mockRoute.params = { id: 'bleak-house' }
    mountView(async () => ({ id: 'bleak-house', title: 'Bleak House' }))
    await flushPromises()

    expect(mockReplace).not.toHaveBeenCalled()
  })

  it('keeps the route when the detail carries no slug', async () => {
    mountView(async () => ({ title: 'Bleak House' }))
    await flushPromises()

    expect(mockReplace).not.toHaveBeenCalled()
  })
})
