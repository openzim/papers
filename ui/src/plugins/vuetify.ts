import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify, type ThemeDefinition } from 'vuetify'
import { createVueI18nAdapter } from 'vuetify/locale/adapters/vue-i18n'
import { useI18n } from 'vue-i18n'
import { i18n, supportedLanguages } from '@/plugins/i18n'
import { THEME_COLORS } from '@/constants/theme'

async function loadVuetify() {
  const PRIMARY = '#1976D2'
  const SECONDARY = '#424242'
  const ACCENT = '#82B1FF'
  const ERROR = '#D32F2F'
  const INFO = '#1976D2'
  const SUCCESS = '#388E3C'
  const WARNING = '#F57C00'
  const BACKGROUND_LIGHT = '#F2F0F0'
  const BACKGROUND_DARK = '#121212'
  const SURFACE_LIGHT = '#FAFAFA'
  const SURFACE_DARK = '#1E1E1E'

  const sharedColors = {
    primary: PRIMARY,
    secondary: SECONDARY,
    accent: ACCENT,
    error: ERROR,
    info: INFO,
    success: SUCCESS,
    warning: WARNING,
    format: THEME_COLORS.FORMAT,
    star: THEME_COLORS.STAR,
    title: THEME_COLORS.TITLE,
    author: THEME_COLORS.AUTHOR,
    authorFocus: THEME_COLORS.AUTHOR_FOCUS,
    description: THEME_COLORS.DESCRIPTION,
    focusBook: THEME_COLORS.FOCUS_BOOK,
    menuActive: THEME_COLORS.MENU_ACTIVE,
    collectionIcon: THEME_COLORS.COLLECTION_ICON,
    collectionIconHover: THEME_COLORS.COLLECTION_ICON_HOVER,
    authorAvatarBgd: THEME_COLORS.AUTHOR_AVATAR_BGD,
    bgd1: THEME_COLORS.BGD_1,
    bgd2: THEME_COLORS.BGD_2,
    bgd3Fill: THEME_COLORS.BGD_3_FILL,
    bgd3Outline: THEME_COLORS.BGD_3_OUTLINE,
    text: THEME_COLORS.TEXT,
    grid: THEME_COLORS.GRID,
    cardBgd: THEME_COLORS.CARD_BGD,
    cardBgdHover: THEME_COLORS.CARD_BGD_HOVER,
    cardBorderHover: THEME_COLORS.CARD_BORDER_HOVER,
    barBorder: THEME_COLORS.BAR_BORDER,
    shelfBgd: THEME_COLORS.SHELF_BGD
  }

  const lightColors = {
    ...sharedColors,
    grid: THEME_COLORS.GRID,
    text: THEME_COLORS.TEXT,
    bgd3Fill: THEME_COLORS.BGD_3_FILL,
    bgd3Outline: THEME_COLORS.BGD_3_OUTLINE
  }

  const darkColors = {
    ...sharedColors,
    grid: THEME_COLORS.GRID_DARK,
    text: THEME_COLORS.TEXT_DARK,
    bgd1: THEME_COLORS.BGD_1_DARK,
    bgd2: THEME_COLORS.BGD_2_DARK,
    bgd3Fill: THEME_COLORS.BGD_3_FILL_DARK,
    bgd3Outline: THEME_COLORS.BGD_3_OUTLINE_DARK,
    focusBook: THEME_COLORS.FOCUS_BOOK_DARK,
    collectionIcon: THEME_COLORS.COLLECTION_ICON_DARK,
    collectionIconHover: THEME_COLORS.COLLECTION_ICON_HOVER_DARK,
    authorAvatarBgd: THEME_COLORS.AUTHOR_AVATAR_BGD_DARK,
    cardBgd: THEME_COLORS.CARD_BGD_DARK,
    cardBgdHover: THEME_COLORS.CARD_BGD_HOVER_DARK,
    cardBorderHover: THEME_COLORS.CARD_BORDER_HOVER_DARK,
    barBorder: THEME_COLORS.BAR_BORDER_DARK,
    shelfBgd: THEME_COLORS.SHELF_BGD_DARK
  }

  const lightTheme: ThemeDefinition = {
    dark: false,
    colors: {
      background: BACKGROUND_LIGHT,
      surface: SURFACE_LIGHT,
      ...lightColors
    }
  }

  const darkTheme: ThemeDefinition = {
    dark: true,
    colors: {
      background: BACKGROUND_DARK,
      surface: SURFACE_DARK,
      ...darkColors
    }
  }

  const rtl: Record<string, boolean> = {}
  for (const lang of supportedLanguages) {
    rtl[lang.code] = lang.rtl
  }

  return createVuetify({
    locale: {
      adapter: createVueI18nAdapter({ i18n, useI18n }),
      rtl
    },
    theme: {
      defaultTheme: 'light',
      variations: {
        colors: ['primary', 'secondary'],
        lighten: 3,
        darken: 3
      },
      themes: {
        light: lightTheme,
        dark: darkTheme
      }
    },
    display: {
      mobileBreakpoint: 'sm',
      thresholds: {
        xs: 500,
        sm: 768,
        md: 1024,
        lg: 1280,
        xl: 1920
      }
    },
    defaults: {
      VBtn: {
        elevation: 2,
        variant: 'elevated'
      },
      VCard: {
        elevation: 2,
        variant: 'elevated'
      }
    }
  })
}

export default loadVuetify
