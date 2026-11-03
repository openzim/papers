/**
 * Component tests for AuthorDetailInfo
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import AuthorDetailInfo from './AuthorDetailInfo.vue'
import type { AuthorDetail, AuthorPreview } from '@/types'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: { en: { languageFilter: { allLanguages: 'All languages' } }, qq: {} }
})

const createAuthor = (overrides?: Partial<AuthorDetail>): AuthorDetail => ({
  id: 'austen-jane',
  displayName: 'Jane Austen',
  sortName: 'Austen',
  birthYear: '1775',
  deathYear: '1817',
  bookCount: 42,
  languages: ['en'],
  bookCountByLanguage: { en: 42 },
  books: [],
  ...overrides
})

const mountInfo = (author: AuthorDetail, authors: AuthorPreview[] = []) =>
  mount(AuthorDetailInfo, {
    props: { author, authors },
    global: {
      plugins: [i18n],
      stubs: {
        AuthorDetailCarousel: true,
        BookDisplay: true,
        EmptyState: true
      }
    }
  })

describe('AuthorDetailInfo', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('Enrichment section', () => {
    // jsdom has no real viewport/matchMedia, so Vuetify's useDisplay() always
    // reports `mobile: true` here, matching AuthorCard's mobile behavior:
    // the empty section is dropped instead of kept for layout spacing.
    it('does not render the about section on mobile when neither bio nor a webpage resource is available', () => {
      const wrapper = mountInfo(createAuthor({ bio: null, webpageResource: null }))

      expect(wrapper.find('.author-card__about').exists()).toBe(false)
    })

    it('does not render the about section on mobile when only a portrait is available', () => {
      const wrapper = mountInfo(
        createAuthor({
          bio: null,
          webpageResource: null,
          portraitPath: './authors/austen-jane.webp'
        })
      )

      expect(wrapper.find('.author-card__about').exists()).toBe(false)
    })

    it('renders the biography when bio is available', () => {
      const wrapper = mountInfo(createAuthor({ bio: 'A gifted novelist.' }))

      const about = wrapper.find('.author-card__about')
      expect(about.exists()).toBe(true)
      expect(wrapper.find('.author-card__bio').text()).toBe('A gifted novelist.')
    })

    it('does not render a standalone portrait in the about section', () => {
      const wrapper = mountInfo(
        createAuthor({ bio: 'A gifted novelist.', portraitPath: './authors/austen-jane.webp' })
      )

      expect(wrapper.find('.author-card__portrait').exists()).toBe(false)
      expect(wrapper.find('.author-card__about img').exists()).toBe(false)
      expect(wrapper.find('.author-card__bio').exists()).toBe(true)
    })

    it('renders the source link when a webpage resource is available', () => {
      const wrapper = mountInfo(
        createAuthor({
          bio: 'A gifted novelist.',
          webpageResource: 'https://en.wikipedia.org/wiki/Jane_Austen'
        })
      )

      const link = wrapper.find('a.author-card__source')
      expect(link.exists()).toBe(true)
      expect(link.attributes('href')).toBe('https://en.wikipedia.org/wiki/Jane_Austen')
      expect(link.attributes('target')).toBe('_blank')
    })
  })
})
