import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { mdiBookshelf, mdiIncognito, mdiInformation, mdiNewspaperVariant, mdiPaw } from '@mdi/js'
import SubjectCollectionIcon from './SubjectCollectionIcon.vue'

function pathFor(subject: string | null, fallback?: string): string | undefined {
  const wrapper = mount(SubjectCollectionIcon, { props: { subject, fallback } })
  return wrapper.find('path').attributes('d')
}

describe('SubjectCollectionIcon', () => {
  it('uses the icon of an Open Textbook Library root subject', () => {
    expect(pathFor('Journalism, Media Studies & Communications')).toBe(mdiNewspaperVariant)
  })

  it('uses the icon of a One More Library category', () => {
    expect(pathFor('Obras generales e información')).toBe(mdiInformation)
  })

  it('uses the icon of a Bibliothèque numérique romande collection', () => {
    expect(pathFor('Policier & Mystère')).toBe(mdiIncognito)
  })

  it('uses the icon of a Littérature jeunesse libre collection', () => {
    expect(pathFor('Animaux')).toBe(mdiPaw)
  })

  it('falls back to the provided icon for an unknown subject', () => {
    expect(pathFor('Unknown', mdiInformation)).toBe(mdiInformation)
  })

  it('falls back to a bookshelf without an explicit fallback', () => {
    expect(pathFor(null)).toBe(mdiBookshelf)
  })
})
