import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { nextTick } from 'vue'
import CollectionCarousel from './CollectionCarousel.vue'
import type { BookPreview } from '@/types'
import loadVuetify from '@/plugins/vuetify'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: {
    en: {
      book: { sameCollectionBooks: 'Books in the same collection' },
      common: { scrollLeft: 'Scroll left', scrollRight: 'Scroll right' }
    },
    qq: {}
  }
})

describe('CollectionCarousel', () => {
  let vuetify: Awaited<ReturnType<typeof loadVuetify>>

  beforeEach(async () => {
    vuetify = await loadVuetify()
  })

  const createBook = (id: number): BookPreview => ({
    id: String(id),
    title: `Book ${id}`,
    author: {
      id: `author-${id}`,
      displayName: `Author ${id}`,
      sortName: `Author ${id}`
    },
    languages: ['en'],
    popularity: 100,
    flames: 2,
    coverPath: null,
    primaryCollection: 'Fiction',
    availableFormats: ['epub'],
    description: `Description ${id}`
  })

  it('progressively renders only the initial batch in mobile track for large book lists', () => {
    const books = Array.from({ length: 50 }, (_, i) => createBook(i + 1))
    const wrapper = mount(CollectionCarousel, {
      props: { books },
      global: {
        plugins: [i18n, vuetify],
        stubs: {
          CollectionBookCard: true,
          CarouselArrow: true
        }
      }
    })

    const desktopCards = wrapper.findAll('.carousel-card-wrapper--desktop')
    expect(desktopCards.length).toBe(5)

    const mobileCards = wrapper.findAll('.carousel-card-wrapper--mobile')
    expect(mobileCards.length).toBe(15)
  })

  it('renders all books when book count is smaller than the batch size', () => {
    const books = Array.from({ length: 8 }, (_, i) => createBook(i + 1))
    const wrapper = mount(CollectionCarousel, {
      props: { books },
      global: {
        plugins: [i18n, vuetify],
        stubs: {
          CollectionBookCard: true,
          CarouselArrow: true
        }
      }
    })

    const mobileCards = wrapper.findAll('.carousel-card-wrapper--mobile')
    expect(mobileCards.length).toBe(8)
  })

  it('loads more items when scrolling near the end of mobile track', async () => {
    const books = Array.from({ length: 50 }, (_, i) => createBook(i + 1))
    const wrapper = mount(CollectionCarousel, {
      props: { books },
      global: {
        plugins: [i18n, vuetify],
        stubs: {
          CollectionBookCard: true,
          CarouselArrow: true
        }
      }
    })

    expect(wrapper.findAll('.carousel-card-wrapper--mobile').length).toBe(15)

    const track = wrapper.find('.collection-books-scroll').element as HTMLElement
    Object.defineProperty(track, 'scrollWidth', { value: 2400, configurable: true })
    Object.defineProperty(track, 'clientWidth', { value: 400, configurable: true })
    Object.defineProperty(track, 'scrollLeft', { value: 1800, configurable: true, writable: true })

    await wrapper.find('.collection-books-scroll').trigger('scroll')
    await nextTick()

    expect(wrapper.findAll('.carousel-card-wrapper--mobile').length).toBe(30)
  })

  it('resets displayed count when props.books changes', async () => {
    const initialBooks = Array.from({ length: 50 }, (_, i) => createBook(i + 1))
    const wrapper = mount(CollectionCarousel, {
      props: { books: initialBooks },
      global: {
        plugins: [i18n, vuetify],
        stubs: {
          CollectionBookCard: true,
          CarouselArrow: true
        }
      }
    })

    const track = wrapper.find('.collection-books-scroll').element as HTMLElement
    Object.defineProperty(track, 'scrollWidth', { value: 2400, configurable: true })
    Object.defineProperty(track, 'clientWidth', { value: 400, configurable: true })
    Object.defineProperty(track, 'scrollLeft', { value: 1800, configurable: true, writable: true })

    await wrapper.find('.collection-books-scroll').trigger('scroll')
    await nextTick()
    expect(wrapper.findAll('.carousel-card-wrapper--mobile').length).toBe(30)

    const newBooks = Array.from({ length: 50 }, (_, i) => createBook(i + 100))
    await wrapper.setProps({ books: newBooks })
    await nextTick()

    expect(wrapper.findAll('.carousel-card-wrapper--mobile').length).toBe(15)
  })
})
