import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { useScrollTrack } from './useScrollTrack'
import { i18n } from '@/plugins/i18n'
import loadVuetify from '@/plugins/vuetify'

describe('useScrollTrack', () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>
  let vuetify: Awaited<ReturnType<typeof loadVuetify>>

  beforeEach(async () => {
    vuetify = await loadVuetify()
    i18n.global.locale.value = 'en'
    addEventListenerSpy = vi.spyOn(window, 'addEventListener')
    removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    vi.restoreAllMocks()
    i18n.global.locale.value = 'en'
  })

  const mountTrack = (cellSelector = '.test-cell') => {
    const TestComponent = defineComponent({
      setup() {
        return useScrollTrack({ cellSelector })
      },
      template: `
        <div>
          <div ref="trackRef" class="track" @scroll.passive="updateScrollState">
            <div class="test-cell"></div>
            <div class="test-cell"></div>
          </div>
        </div>
      `
    })

    return mount(TestComponent, {
      global: {
        plugins: [vuetify]
      }
    })
  }

  it('initializes trackRef and default state', () => {
    const wrapper = mountTrack()
    expect(wrapper.vm.hasPrevious).toBe(false)
    expect(wrapper.vm.hasNext).toBe(false)
    expect(wrapper.vm.trackRef).toBeDefined()
  })

  it('registers and unregisters window resize listeners', () => {
    const wrapper = mountTrack()
    expect(addEventListenerSpy).toHaveBeenCalledWith('resize', expect.any(Function))

    wrapper.unmount()
    expect(removeEventListenerSpy).toHaveBeenCalledWith('resize', expect.any(Function))
  })

  it('updates state when track receives a scroll event', async () => {
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement

    Object.defineProperty(track, 'scrollWidth', { value: 500, configurable: true })
    Object.defineProperty(track, 'clientWidth', { value: 200, configurable: true })
    Object.defineProperty(track, 'scrollLeft', { value: 150, configurable: true })

    await wrapper.find('.track').trigger('scroll')

    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)
  })

  it('updates hasPrevious and hasNext accurately in LTR', async () => {
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement

    // Mock dimensions: total scrollWidth 500, visible width 200 => maxScroll = 300
    Object.defineProperty(track, 'scrollWidth', { value: 500, configurable: true })
    Object.defineProperty(track, 'clientWidth', { value: 200, configurable: true })

    // At start
    Object.defineProperty(track, 'scrollLeft', { value: 0, configurable: true })
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(false)
    expect(wrapper.vm.hasNext).toBe(true)

    // In middle
    Object.defineProperty(track, 'scrollLeft', { value: 150, configurable: true })
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)

    // At end
    Object.defineProperty(track, 'scrollLeft', { value: 300, configurable: true })
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(false)
  })

  it('updates hasPrevious and hasNext accurately in RTL', async () => {
    i18n.global.locale.value = 'ar'
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement

    Object.defineProperty(track, 'scrollWidth', { value: 500, configurable: true })
    Object.defineProperty(track, 'clientWidth', { value: 200, configurable: true })

    // In RTL, at start (scrollLeft = 0)
    Object.defineProperty(track, 'scrollLeft', { value: 0, configurable: true })
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(false)
    expect(wrapper.vm.hasNext).toBe(true)

    // In RTL, scrolled left (negative scrollLeft)
    Object.defineProperty(track, 'scrollLeft', { value: -150, configurable: true })
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)

    // In RTL, at end
    Object.defineProperty(track, 'scrollLeft', { value: -300, configurable: true })
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(false)
  })

  it('scrolls by cell width in LTR', async () => {
    const wrapper = mountTrack('.test-cell')
    const track = wrapper.vm.trackRef as HTMLElement
    const cell = track.querySelector('.test-cell') as HTMLElement

    Object.defineProperty(cell, 'clientWidth', { value: 100, configurable: true })
    track.scrollBy = vi.fn()

    wrapper.vm.shiftNext()
    expect(track.scrollBy).toHaveBeenCalledWith({ left: 100, behavior: 'smooth' })

    wrapper.vm.shiftPrevious()
    expect(track.scrollBy).toHaveBeenCalledWith({ left: -100, behavior: 'smooth' })
  })

  it('flips scroll sign when in RTL mode', async () => {
    i18n.global.locale.value = 'ar'
    const wrapper = mountTrack('.test-cell')
    const track = wrapper.vm.trackRef as HTMLElement
    const cell = track.querySelector('.test-cell') as HTMLElement

    Object.defineProperty(cell, 'clientWidth', { value: 100, configurable: true })
    track.scrollBy = vi.fn()

    wrapper.vm.shiftNext()
    expect(track.scrollBy).toHaveBeenCalledWith({ left: -100, behavior: 'smooth' })

    wrapper.vm.shiftPrevious()
    expect(track.scrollBy).toHaveBeenCalledWith({ left: 100, behavior: 'smooth' })
  })

  it('falls back to track.clientWidth / 5 if cellSelector is not found', async () => {
    const wrapper = mountTrack('.non-existent-cell')
    const track = wrapper.vm.trackRef as HTMLElement
    Object.defineProperty(track, 'clientWidth', { value: 500, configurable: true })
    track.scrollBy = vi.fn()

    wrapper.vm.shiftNext()
    expect(track.scrollBy).toHaveBeenCalledWith({ left: 100, behavior: 'smooth' })
  })
})
