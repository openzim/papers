import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { useScrollTrack } from './useScrollTrack'
import { i18n } from '@/plugins/i18n'
import loadVuetify from '@/plugins/vuetify'

const VIEWPORT_WIDTH = 200
const CELL_WIDTH = 100
const CELL_COUNT = 4

const makeRect = (left: number, width: number): DOMRect =>
  ({
    x: left,
    y: 0,
    left,
    top: 0,
    width,
    height: 40,
    right: left + width,
    bottom: 40,
    toJSON: () => ({})
  }) as DOMRect

const stubRect = (element: Element, left: number, width: number) => {
  Object.defineProperty(element, 'getBoundingClientRect', {
    configurable: true,
    value: () => makeRect(left, width)
  })
}

const stubLayout = (track: HTMLElement, scrolledFromStart: number, isRtl: boolean) => {
  stubRect(track, 0, VIEWPORT_WIDTH)
  Array.from(track.children).forEach((cell, index) => {
    const offsetFromStart = index * CELL_WIDTH - scrolledFromStart
    stubRect(
      cell,
      isRtl ? VIEWPORT_WIDTH - CELL_WIDTH - offsetFromStart : offsetFromStart,
      CELL_WIDTH
    )
  })
}

const stubCellWidth = (track: HTMLElement) => {
  Array.from(track.children).forEach((cell) => {
    Object.defineProperty(cell, 'clientWidth', { configurable: true, value: CELL_WIDTH })
  })
}

const MAX_SCROLL = CELL_COUNT * CELL_WIDTH - VIEWPORT_WIDTH

type Convention = 'negative-range' | 'reversed' | 'legacy'

const CONVENTIONS = [{ name: 'negative-range' }, { name: 'reversed' }, { name: 'legacy' }] as const

const toScrollLeft = (scrolled: number, isRtl: boolean, convention: Convention) => {
  if (!isRtl) return scrolled
  if (convention === 'negative-range') return -scrolled
  return convention === 'reversed' ? MAX_SCROLL - scrolled : scrolled
}

const toScrolled = (scrollLeft: number, isRtl: boolean, convention: Convention) => {
  if (!isRtl) return scrollLeft
  if (convention === 'negative-range') return -scrollLeft
  return convention === 'reversed' ? MAX_SCROLL - scrollLeft : scrollLeft
}

interface FakeTrackEngine {
  scrolled: number
  positionsAtScroll: number[]
}

const stubScrollEngine = (
  track: HTMLElement,
  layout: {
    scrolled: number
    isRtl: boolean
    convention: Convention
    snapsToCells?: boolean
  }
): FakeTrackEngine => {
  const { isRtl, convention, snapsToCells = false } = layout
  const engine: FakeTrackEngine = { scrolled: layout.scrolled, positionsAtScroll: [] }

  const apply = (scrollLeft: number) => {
    const scrolled = toScrolled(scrollLeft, isRtl, convention)
    const clamped = Math.min(MAX_SCROLL, Math.max(0, scrolled))
    engine.scrolled = snapsToCells ? Math.round(clamped / CELL_WIDTH) * CELL_WIDTH : clamped
    stubLayout(track, engine.scrolled, isRtl)
    track.dispatchEvent(new Event('scroll'))
  }

  Object.defineProperty(track, 'scrollLeft', {
    configurable: true,
    get: () => toScrollLeft(engine.scrolled, isRtl, convention),
    set: apply
  })

  track.scrollBy = vi.fn((options?: number | ScrollToOptions, y?: number) => {
    engine.positionsAtScroll.push(track.scrollLeft)
    const delta = typeof options === 'number' ? (y ?? 0) : (options?.left ?? 0)
    apply(track.scrollLeft + delta)
  })

  stubLayout(track, layout.scrolled, isRtl)
  return engine
}

describe('useScrollTrack', () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>
  let scrollIntoViewSpy: Mock<() => void>
  let vuetify: Awaited<ReturnType<typeof loadVuetify>>

  beforeEach(async () => {
    vuetify = await loadVuetify()
    i18n.global.locale.value = 'en'
    addEventListenerSpy = vi.spyOn(window, 'addEventListener')
    removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')
    scrollIntoViewSpy = vi.fn<() => void>()
    Element.prototype.scrollIntoView = scrollIntoViewSpy
  })

  afterEach(() => {
    delete (Element.prototype as Partial<typeof Element.prototype>).scrollIntoView
    vi.restoreAllMocks()
    i18n.global.locale.value = 'en'
  })

  const mountTrack = (cellSelector = '.test-cell', cellCount = CELL_COUNT) => {
    const TestComponent = defineComponent({
      setup() {
        return useScrollTrack({ cellSelector })
      },
      template: `
        <div>
          <div ref="trackRef" class="track" @scroll.passive="updateScrollState">
            <div v-for="cell in cellCount" :key="cell" class="test-cell"></div>
          </div>
        </div>
      `,
      data: () => ({ cellCount })
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
    stubLayout(track, CELL_WIDTH, false)

    await wrapper.find('.track').trigger('scroll')

    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)
  })

  it('updates hasPrevious and hasNext accurately in LTR', () => {
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement

    stubLayout(track, 0, false)
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(false)
    expect(wrapper.vm.hasNext).toBe(true)

    stubLayout(track, CELL_WIDTH, false)
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)

    stubLayout(track, 2 * CELL_WIDTH, false)
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(false)
  })

  it('updates hasPrevious and hasNext accurately in RTL', () => {
    i18n.global.locale.value = 'ps'
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement

    stubLayout(track, 0, true)
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(false)
    expect(wrapper.vm.hasNext).toBe(true)

    stubLayout(track, CELL_WIDTH, true)
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)

    stubLayout(track, 2 * CELL_WIDTH, true)
    wrapper.vm.updateScrollState()
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(false)
  })

  it.each([
    { name: 'negative-range', readings: [0, -100, -200] },
    { name: 'reversed, always-positive', readings: [200, 100, 0] },
    { name: 'legacy, always-positive', readings: [0, 100, 200] }
  ])('reads the scroll state from geometry alone under the $name convention', ({ readings }) => {
    i18n.global.locale.value = 'ps'
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement

    readings.forEach((scrollLeft, step) => {
      Object.defineProperty(track, 'scrollLeft', { configurable: true, value: scrollLeft })
      stubLayout(track, step * CELL_WIDTH, true)
      wrapper.vm.updateScrollState()
      expect(wrapper.vm.hasPrevious).toBe(step > 0)
      expect(wrapper.vm.hasNext).toBe(step < readings.length - 1)
    })
  })

  it('steps one cell per click in LTR', () => {
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubCellWidth(track)
    const engine = stubScrollEngine(track, {
      scrolled: 0,
      isRtl: false,
      convention: 'negative-range'
    })

    wrapper.vm.shiftNext()
    expect(engine.scrolled).toBe(CELL_WIDTH)
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)

    wrapper.vm.shiftNext()
    expect(engine.scrolled).toBe(MAX_SCROLL)
    expect(wrapper.vm.hasNext).toBe(false)

    wrapper.vm.shiftPrevious()
    expect(engine.scrolled).toBe(CELL_WIDTH)
    expect(scrollIntoViewSpy).not.toHaveBeenCalled()
  })

  it.each(CONVENTIONS)('steps one cell per click in RTL under the $name convention', ({ name }) => {
    i18n.global.locale.value = 'ps'
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubCellWidth(track)
    const engine = stubScrollEngine(track, {
      scrolled: 0,
      isRtl: true,
      convention: name,
      snapsToCells: true
    })

    wrapper.vm.shiftNext()
    expect(engine.scrolled).toBe(CELL_WIDTH)
    expect(wrapper.vm.hasPrevious).toBe(true)
    expect(wrapper.vm.hasNext).toBe(true)

    wrapper.vm.shiftNext()
    expect(engine.scrolled).toBe(MAX_SCROLL)
    expect(wrapper.vm.hasNext).toBe(false)

    wrapper.vm.shiftPrevious()
    expect(engine.scrolled).toBe(CELL_WIDTH)
    expect(scrollIntoViewSpy).not.toHaveBeenCalled()
  })

  it.each([
    { name: 'negative-range', left: -CELL_WIDTH },
    { name: 'reversed', left: -CELL_WIDTH },
    { name: 'legacy', left: CELL_WIDTH }
  ] as const)(
    'derives the RTL arrow delta from the engine instead of the writing direction ($name)',
    ({ name, left }) => {
      i18n.global.locale.value = 'ps'
      const wrapper = mountTrack()
      const track = wrapper.vm.trackRef as HTMLElement
      stubCellWidth(track)
      stubScrollEngine(track, {
        scrolled: CELL_WIDTH,
        isRtl: true,
        convention: name,
        snapsToCells: true
      })

      wrapper.vm.shiftNext()
      expect(track.scrollBy).toHaveBeenLastCalledWith({ left, behavior: 'smooth' })
    }
  )

  it('leaves the scroll position where it was while probing the convention', () => {
    i18n.global.locale.value = 'ps'
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubCellWidth(track)
    const engine = stubScrollEngine(track, {
      scrolled: CELL_WIDTH,
      isRtl: true,
      convention: 'reversed'
    })

    wrapper.vm.shiftNext()
    expect(engine.positionsAtScroll).toEqual([MAX_SCROLL - CELL_WIDTH])
  })

  it('aligns a cell to the inline start in LTR', () => {
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubCellWidth(track)
    const engine = stubScrollEngine(track, {
      scrolled: 0,
      isRtl: false,
      convention: 'negative-range'
    })

    wrapper.vm.alignCell(track.children[1])
    expect(engine.scrolled).toBe(CELL_WIDTH)
    expect(scrollIntoViewSpy).not.toHaveBeenCalled()
  })

  it.each(CONVENTIONS)('aligns a cell to the inline start in RTL ($name)', ({ name }) => {
    i18n.global.locale.value = 'ps'
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubCellWidth(track)
    const engine = stubScrollEngine(track, {
      scrolled: 0,
      isRtl: true,
      convention: name,
      snapsToCells: true
    })

    wrapper.vm.alignCell(track.children[2])
    expect(engine.scrolled).toBe(MAX_SCROLL)
    expect(scrollIntoViewSpy).not.toHaveBeenCalled()
  })

  it('does not move the track when the cell is already aligned', () => {
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubCellWidth(track)
    const engine = stubScrollEngine(track, {
      scrolled: CELL_WIDTH,
      isRtl: false,
      convention: 'negative-range'
    })

    wrapper.vm.alignCell(track.children[1])
    expect(track.scrollBy).not.toHaveBeenCalled()
    expect(engine.scrolled).toBe(CELL_WIDTH)
  })

  it('aligns a cell at a distance from the inline start in RTL under every convention', () => {
    for (const { name } of CONVENTIONS) {
      i18n.global.locale.value = 'ps'
      const wrapper = mountTrack()
      const track = wrapper.vm.trackRef as HTMLElement
      stubCellWidth(track)
      const engine = stubScrollEngine(track, {
        scrolled: MAX_SCROLL - CELL_WIDTH,
        isRtl: true,
        convention: name
      })

      wrapper.vm.alignCell(track.children[1], -CELL_WIDTH)
      expect(engine.scrolled).toBe(2 * CELL_WIDTH)
      expect(scrollIntoViewSpy).not.toHaveBeenCalled()
    }
  })

  it('measures a cell from the inline start in both writing directions', () => {
    const ltr = mountTrack()
    const ltrTrack = ltr.vm.trackRef as HTMLElement
    stubLayout(ltrTrack, 0, false)
    expect(ltr.vm.distanceOf(ltrTrack.children[2])).toBe(2 * CELL_WIDTH)

    i18n.global.locale.value = 'ps'
    const rtl = mountTrack()
    const rtlTrack = rtl.vm.trackRef as HTMLElement
    stubLayout(rtlTrack, 0, true)
    expect(rtl.vm.distanceOf(rtlTrack.children[2])).toBe(2 * CELL_WIDTH)
  })

  it('reports the hidden distance at each inline edge from the cards, not from scrollLeft', () => {
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubLayout(track, 2 * CELL_WIDTH, false)
    Object.defineProperty(track, 'scrollLeft', { configurable: true, value: 0 })

    expect(wrapper.vm.distanceToStart()).toBe(2 * CELL_WIDTH)
    expect(wrapper.vm.distanceToEnd()).toBe(0)

    i18n.global.locale.value = 'ps'
    const rtl = mountTrack()
    const rtlTrack = rtl.vm.trackRef as HTMLElement
    stubLayout(rtlTrack, 2 * CELL_WIDTH, true)
    Object.defineProperty(rtlTrack, 'scrollLeft', { configurable: true, value: 0 })

    expect(rtl.vm.distanceToStart()).toBe(2 * CELL_WIDTH)
    expect(rtl.vm.distanceToEnd()).toBe(0)
  })

  it('falls back to the writing direction when the engine reports no usable overflow', () => {
    i18n.global.locale.value = 'ps'
    const wrapper = mountTrack()
    const track = wrapper.vm.trackRef as HTMLElement
    stubCellWidth(track)
    stubLayout(track, CELL_WIDTH, true)
    track.scrollBy = vi.fn()

    wrapper.vm.shiftNext()
    expect(track.scrollBy).toHaveBeenCalledWith({ left: -CELL_WIDTH, behavior: 'smooth' })
    expect(scrollIntoViewSpy).not.toHaveBeenCalled()
  })

  it('falls back to a fifth of the track width when cellSelector matches nothing', () => {
    const wrapper = mountTrack('.non-existent-cell')
    const track = wrapper.vm.trackRef as HTMLElement
    Object.defineProperty(track, 'clientWidth', { configurable: true, value: VIEWPORT_WIDTH })
    track.scrollBy = vi.fn()

    wrapper.vm.shiftNext()
    expect(track.scrollBy).toHaveBeenCalledWith({
      left: VIEWPORT_WIDTH / 5,
      behavior: 'smooth'
    })
    expect(scrollIntoViewSpy).not.toHaveBeenCalled()
  })
})
