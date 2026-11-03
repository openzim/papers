import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMainStore } from '@/stores/main'
import { useFormatters } from '@/composables/useFormatters'

export interface LanguageFilterOption {
  code: string
  label: string
}

/**
 * The single, global book-language filter: current selection plus the
 * available options, derived from `config.bookLanguages` so pages don't
 * need the full books catalog loaded just to populate the control.
 */
export function useLanguageFilter() {
  const main = useMainStore()
  const { t } = useI18n()
  const { formatLanguages } = useFormatters()

  const selectedLanguage = computed<string | null>({
    get: () => main.selectedLanguage,
    set: (value) => {
      main.selectedLanguage = value
    }
  })

  const languageOptions = computed<LanguageFilterOption[]>(() =>
    (main.config?.bookLanguages ?? [])
      .map((code) => ({ code, label: formatLanguages([code]) }))
      .sort((a, b) => a.label.localeCompare(b.label))
  )

  const selectedLanguageLabel = computed(() =>
    selectedLanguage.value === null
      ? t('languageFilter.allLanguages')
      : formatLanguages([selectedLanguage.value])
  )

  return { selectedLanguage, languageOptions, selectedLanguageLabel }
}
