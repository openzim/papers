import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { nextTick } from 'vue'
import AuthorDetailCarousel from './AuthorDetailCarousel.vue'
import type { AuthorPreview, AuthorDetail } from '@/types'
import loadVuetify from '@/plugins/vuetify'
import { i18n as appI18n } from '@/plugins/i18n'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: {
    en: {
      common: { previous: 'Previous', next: 'Next' }
    },
    ps: {
      common: { previous: 'Previous', next: 'Next' }
    },
    qq: {}
  }
})

const VIEWPORT_WIDTH = 1000
const CELL_WIDTH = 200
const INITIAL_CELLS = 30
const BATCH_SIZE = 15

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

const nativeGetBoundingClientRect = Element.prototype.getBoundingClientRect

let restoreTrack: (() => void) | null = null

const stubTrack = (track: HTMLElement, scrolledFromStart: number, isRtl: boolean) => {
  const state = { scrolled: scrolledFromStart }

  const maxScroll = () => Math.max(0, track.children.length * CELL_WIDTH - VIEWPORT_WIDTH)

  Element.prototype.getBoundingClientRect = function (this: Element): DOMRect {
    if (this === track) return makeRect(0, VIEWPORT_WIDTH)
    const index = Array.from(track.children).indexOf(this)
    if (index < 0) return makeRect(0, 0)
    const offsetFromStart = index * CELL_WIDTH - state.scrolled
    const left = isRtl ? VIEWPORT_WIDTH - CELL_WIDTH - offsetFromStart : offsetFromStart
    return makeRect(left, CELL_WIDTH)
  }

  Object.defineProperty(track, 'scrollLeft', {
    configurable: true,
    get: () => (isRtl ? -state.scrolled : state.scrolled),
    set: (value: number) => {
      const scrolled = isRtl ? -value : value
      state.scrolled = Math.min(maxScroll(), Math.max(0, scrolled))
      track.dispatchEvent(new Event('scroll'))
    }
  })

  track.scrollBy = (options?: number | ScrollToOptions) => {
    const delta = typeof options === 'number' ? options : (options?.left ?? 0)
    track.scrollLeft = (isRtl ? -state.scrolled : state.scrolled) + delta
  }

  restoreTrack = () => {
    Element.prototype.getBoundingClientRect = nativeGetBoundingClientRect
    delete (track as Partial<HTMLElement>).scrollBy
  }

  return {
    scrolled: () => state.scrolled,
    leftOf: (element: Element) => element.getBoundingClientRect().left
  }
}

describe('AuthorDetailCarousel', () => {
  let vuetify: Awaited<ReturnType<typeof loadVuetify>>

  beforeEach(async () => {
    vuetify = await loadVuetify()
  })

  afterEach(() => {
    restoreTrack?.()
    restoreTrack = null
    i18n.global.locale.value = 'en'
    appI18n.global.locale.value = 'en'
  })

  const createAuthorPreview = (id: number): AuthorPreview => ({
    id: String(id),
    displayName: `Author ${String(id).padStart(3, '0')}`,
    sortName: `Author ${String(id).padStart(3, '0')}`,
    bookCount: 2,
    languages: ['en'],
    bookCountByLanguage: { en: 2 }
  })

  const createAuthorDetail = (id: number): AuthorDetail => ({
    ...createAuthorPreview(id),
    birthYear: null,
    deathYear: null,
    books: []
  })

  const mountCarousel = async (isRtl = false) => {
    if (isRtl) {
      i18n.global.locale.value = 'ps'
      appI18n.global.locale.value = 'ps'
    }
    const wrapper = mount(AuthorDetailCarousel, {
      props: {
        authors: Array.from({ length: 100 }, (_, i) => createAuthorPreview(i + 1)),
        currentAuthor: createAuthorDetail(50)
      },
      global: {
        plugins: [i18n, vuetify],
        stubs: {
          AuthorCard: true,
          CarouselArrow: true
        }
      }
    })
    await nextTick()
    return wrapper
  }

  const trackOf = (wrapper: VueWrapper) => wrapper.find('.carousel-track').element as HTMLElement

  const currentCellIndex = (wrapper: VueWrapper) => cellIndex(wrapper, 'carousel-cell--current')

  const cellIndex = (wrapper: VueWrapper, selector: string) =>
    wrapper.findAll('.carousel-cell').findIndex((cell) => cell.classes().includes(selector))

  it('renders a windowed slice around the current author for large author lists', () => {
    const authors = Array.from({ length: 100 }, (_, i) => createAuthorPreview(i + 1))
    const currentAuthor = createAuthorDetail(50)

    const wrapper = mount(AuthorDetailCarousel, {
      props: { authors, currentAuthor },
      global: {
        plugins: [i18n, vuetify],
        stubs: {
          AuthorCard: true,
          CarouselArrow: true
        }
      }
    })

    const cells = wrapper.findAll('.carousel-cell')
    expect(cells.length).toBe(INITIAL_CELLS)
    expect(currentCellIndex(wrapper)).toBe(10)
  })

  it('renders all authors when total count is small', () => {
    const authors = Array.from({ length: 5 }, (_, i) => createAuthorPreview(i + 1))
    const currentAuthor = createAuthorDetail(3)

    const wrapper = mount(AuthorDetailCarousel, {
      props: { authors, currentAuthor },
      global: {
        plugins: [i18n, vuetify],
        stubs: {
          AuthorCard: true,
          CarouselArrow: true
        }
      }
    })

    const cells = wrapper.findAll('.carousel-cell')
    expect(cells.length).toBe(5)
    expect(wrapper.find('.carousel-cell--current').exists()).toBe(true)
  })

  it('loads more authors when scrolling forward near the inline end', async () => {
    const wrapper = await mountCarousel()
    stubTrack(trackOf(wrapper), 4800, false)

    await wrapper.find('.carousel-track').trigger('scroll')
    await nextTick()

    expect(wrapper.findAll('.carousel-cell')).toHaveLength(INITIAL_CELLS + BATCH_SIZE)
    expect(currentCellIndex(wrapper)).toBe(10)
  })

  it('loads earlier authors when scrolling backward near the inline start', async () => {
    const wrapper = await mountCarousel()
    stubTrack(trackOf(wrapper), 200, false)

    await wrapper.find('.carousel-track').trigger('scroll')
    await nextTick()

    expect(wrapper.findAll('.carousel-cell')).toHaveLength(INITIAL_CELLS + BATCH_SIZE)
    expect(currentCellIndex(wrapper)).toBe(10 + BATCH_SIZE)
  })

  it('measures both edges from card geometry in RTL, not from scrollLeft', async () => {
    const wrapper = await mountCarousel(true)
    const track = trackOf(wrapper)
    stubTrack(track, 4800, true)

    await wrapper.find('.carousel-track').trigger('scroll')
    await nextTick()

    expect(wrapper.findAll('.carousel-cell')).toHaveLength(INITIAL_CELLS + BATCH_SIZE)
    expect(currentCellIndex(wrapper)).toBe(10)

    stubTrack(track, 200, true)
    await wrapper.find('.carousel-track').trigger('scroll')
    await nextTick()

    expect(wrapper.findAll('.carousel-cell')).toHaveLength(INITIAL_CELLS + 2 * BATCH_SIZE)
    expect(currentCellIndex(wrapper)).toBe(10 + BATCH_SIZE)
  })

  it('keeps the cards on screen where they were when loading earlier authors', async () => {
    const wrapper = await mountCarousel()
    const track = trackOf(wrapper)
    const engine = stubTrack(track, 200, false)
    const anchor = track.children[0]
    const anchorLeft = engine.leftOf(anchor)

    await wrapper.find('.carousel-track').trigger('scroll')
    await nextTick()

    expect(anchorLeft).toBe(-200)
    expect(engine.scrolled()).toBe(200 + BATCH_SIZE * CELL_WIDTH)
    expect(engine.leftOf(anchor)).toBe(anchorLeft)
  })
})
