import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { nextTick } from 'vue'
import AuthorDetailCarousel from './AuthorDetailCarousel.vue'
import type { AuthorPreview, AuthorDetail } from '@/types'
import loadVuetify from '@/plugins/vuetify'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: {
    en: {
      common: { previous: 'Previous', next: 'Next' }
    },
    qq: {}
  }
})

describe('AuthorDetailCarousel', () => {
  let vuetify: Awaited<ReturnType<typeof loadVuetify>>

  beforeEach(async () => {
    vuetify = await loadVuetify()
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
    expect(cells.length).toBeLessThan(40)
    expect(cells.length).toBeGreaterThanOrEqual(30)

    const currentCell = wrapper.find('.carousel-cell--current')
    expect(currentCell.exists()).toBe(true)
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

  it('loads more authors when scrolling forward near the end', async () => {
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

    const initialCount = wrapper.findAll('.carousel-cell').length

    const track = wrapper.find('.carousel-track').element as HTMLElement
    Object.defineProperty(track, 'scrollWidth', { value: 3000, configurable: true })
    Object.defineProperty(track, 'clientWidth', { value: 1000, configurable: true })
    Object.defineProperty(track, 'scrollLeft', { value: 1800, configurable: true, writable: true })

    await wrapper.find('.carousel-track').trigger('scroll')
    await nextTick()

    const newCount = wrapper.findAll('.carousel-cell').length
    expect(newCount).toBeGreaterThan(initialCount)
  })

  it('loads earlier authors when scrolling backward near the start', async () => {
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

    const initialCount = wrapper.findAll('.carousel-cell').length

    const track = wrapper.find('.carousel-track').element as HTMLElement
    Object.defineProperty(track, 'scrollWidth', { value: 3000, configurable: true })
    Object.defineProperty(track, 'clientWidth', { value: 1000, configurable: true })
    Object.defineProperty(track, 'scrollLeft', { value: 200, configurable: true, writable: true })

    await wrapper.find('.carousel-track').trigger('scroll')
    await nextTick()

    const newCount = wrapper.findAll('.carousel-cell').length
    expect(newCount).toBeGreaterThan(initialCount)
  })
})
