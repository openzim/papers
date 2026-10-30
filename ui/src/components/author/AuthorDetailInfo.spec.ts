/**
 * Component tests for AuthorDetailInfo
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AuthorDetailInfo from './AuthorDetailInfo.vue'
import type { AuthorDetail, AuthorPreview } from '@/types'

const createAuthor = (overrides?: Partial<AuthorDetail>): AuthorDetail => ({
  id: 'austen-jane',
  name: 'Jane Austen',
  sortName: 'Austen',
  birthYear: '1775',
  deathYear: '1817',
  bookCount: 42,
  books: [],
  ...overrides
})

const mountInfo = (author: AuthorDetail, authors: AuthorPreview[] = []) =>
  mount(AuthorDetailInfo, {
    props: { author, authors },
    global: {
      stubs: {
        AuthorDetailCarousel: true,
        BookDisplay: true,
        EmptyState: true
      }
    }
  })

describe('AuthorDetailInfo', () => {
  describe('Enrichment section', () => {
    it('renders an empty about section when neither bio nor a webpage resource is available', () => {
      const wrapper = mountInfo(createAuthor({ bio: null, webpageResource: null }))

      // The section is kept (empty) so it still occupies its space in the layout
      const about = wrapper.find('.author-card__about')
      expect(about.exists()).toBe(true)
      expect(about.element.children).toHaveLength(0)
      expect(about.text()).toBe('')
    })

    it('renders an empty about section when only a portrait is available', () => {
      const wrapper = mountInfo(
        createAuthor({
          bio: null,
          webpageResource: null,
          portraitPath: './authors/austen-jane.webp'
        })
      )

      const about = wrapper.find('.author-card__about')
      expect(about.exists()).toBe(true)
      expect(about.element.children).toHaveLength(0)
      expect(about.text()).toBe('')
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
