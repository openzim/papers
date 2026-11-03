import { describe, it, expect } from 'vitest'
import loadVuetify from './vuetify'
import { i18n } from './i18n'

describe('vuetify plugin', () => {
  it('switches to RTL when an RTL locale is selected', async () => {
    const vuetify = await loadVuetify()
    i18n.global.locale.value = 'en'
    expect(vuetify.locale.isRtl.value).toBe(false)

    i18n.global.locale.value = 'ps'
    expect(vuetify.locale.isRtl.value).toBe(true)

    i18n.global.locale.value = 'en'
    expect(vuetify.locale.isRtl.value).toBe(false)
  })

  it('uses a dark-specific semantic palette', async () => {
    const vuetify = await loadVuetify()
    const { light, dark } = vuetify.theme.themes.value
    const semanticColors = ['info', 'error', 'success', 'warning'] as const

    for (const color of semanticColors) {
      expect(dark.colors[color]).not.toBe(light.colors[color])
    }
  })
})
