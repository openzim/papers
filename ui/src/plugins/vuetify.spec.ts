import { describe, it, expect } from 'vitest'
import loadVuetify from './vuetify'
import { i18n } from './i18n'

describe('vuetify plugin', () => {
  it('switches to RTL when an RTL locale is selected', async () => {
    const vuetify = await loadVuetify()
    i18n.global.locale.value = 'en'
    expect(vuetify.locale.isRtl.value).toBe(false)

    i18n.global.locale.value = 'ar'
    expect(vuetify.locale.isRtl.value).toBe(true)

    i18n.global.locale.value = 'en'
    expect(vuetify.locale.isRtl.value).toBe(false)
  })
})
