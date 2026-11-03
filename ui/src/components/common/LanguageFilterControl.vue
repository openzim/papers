<script setup lang="ts">
/**
 * Selecting a language here updates the shared store state, so it filters
 * every view (books, authors, collections, home), not just this page.
 */
import { ref, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDisplay } from 'vuetify'
import { useLanguageFilter } from '@/composables/useLanguageFilter'
import { LAYOUT, TYPOGRAPHY } from '@/constants/theme'

// Material Symbols "globe_book" (outlined), not available in @mdi/js
const GLOBE_BOOK_ICON_PATH =
  'M3.08,13q-0.02-0.25-0.04-0.5T3.03,12q0-1.88 0.7-3.51T5.65,5.64Q6.88,4.42 8.5,3.71T12,3t3.51,0.71t2.85,1.93t1.93,2.85T21,12q0,0.25-0.01,0.5T20.95,13H18.93q0.05-0.25 0.06-0.5T19,12t-0.01-0.5T18.93,11H15.98Q16,11.25 16,11.5T16,12t0,0.5T15.98,13H14q0-0.2 0-0.41q0-0.21 0-0.41q0-0.3-0.01-0.6T13.95,11H10.08q-0.03,0.27-0.04,0.57t-0.01,0.6q0,0.2 0,0.41t0,0.41H8.05q-0.03-0.25-0.03-0.5t0-0.5t0-0.5T8.05,11H5.1q-0.05,0.25-0.06,0.5T5.03,12t0.01,0.5T5.1,13H3.08ZM5.7,9H8.28q0.2-1.07 0.5-1.94T9.43,5.5Q8.23,5.95 7.25,6.86Q6.28,7.77 5.7,9Zm4.65,0h3.3Q13.4,7.93 13.03,6.9Q12.65,5.88 12,5q-0.65,0.88-1.04,1.9Q10.58,7.93 10.35,9Zm5.4,0h2.57q-0.57-1.23-1.56-2.14Q15.78,5.95 14.58,5.5q0.35,0.75 0.66,1.59Q15.55,7.93 15.75,9ZM11,21V20q0-1.25-0.88-2.13T8,17H2V15H8q1.2,0 2.24,0.53T12,17q0.73-0.95 1.76-1.47T16,15h6v2H16q-1.25,0-2.13,0.88T13,20v1H11Z'

const { t } = useI18n()
const { mobile } = useDisplay()
const { selectedLanguage, languageOptions, selectedLanguageLabel } = useLanguageFilter()

const isOpen = ref(false)

function select(code: string | null) {
  selectedLanguage.value = code
  isOpen.value = false
}

function closeOnOutsideClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.language-filter')) {
    isOpen.value = false
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('click', closeOnOutsideClick)
  onUnmounted(() => document.removeEventListener('click', closeOnOutsideClick))
}
</script>

<template>
  <div class="language-filter">
    <button
      class="language-filter__trigger"
      type="button"
      :aria-label="t('languageFilter.trigger')"
      aria-haspopup="listbox"
      :aria-expanded="isOpen"
      @click.stop="isOpen = !isOpen"
    >
      <span v-if="!mobile" class="language-filter__label">{{ selectedLanguageLabel }}</span>
      <svg class="language-filter__icon" viewBox="0 0 24 24" aria-hidden="true">
        <path :d="GLOBE_BOOK_ICON_PATH" />
      </svg>
    </button>

    <ul v-if="isOpen" class="language-filter__menu" role="listbox">
      <li
        class="language-filter__item"
        :class="{ 'language-filter__item--active': selectedLanguage === null }"
        role="option"
        :aria-selected="selectedLanguage === null"
        @click="select(null)"
      >
        {{ t('languageFilter.allLanguages') }}
      </li>
      <li
        v-for="option in languageOptions"
        :key="option.code"
        class="language-filter__item"
        :class="{ 'language-filter__item--active': option.code === selectedLanguage }"
        role="option"
        :aria-selected="option.code === selectedLanguage"
        @click="select(option.code)"
      >
        {{ option.label }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.language-filter {
  position: relative;
  margin-inline-start: auto;
  margin-inline-end: v-bind(LAYOUT.VIEW_PADDING_HORIZONTAL);
}

.language-filter__trigger {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0;
  background: none;
  border: none;
  cursor: pointer;
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.CAPTION_SIZE);
  font-weight: 400;
  color: rgb(var(--v-theme-text));
  opacity: 0.85;
}

.language-filter__trigger:hover {
  opacity: 1;
}

.language-filter__icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: rgba(var(--v-theme-text), 0.85);
}

.language-filter__label {
  white-space: nowrap;
  padding-inline-end: 0.5rem;
}

.language-filter__menu {
  position: absolute;
  top: calc(100% + 4px);
  inset-inline-end: 0;
  min-width: 160px;
  background: rgb(var(--v-theme-background));
  border: 1px solid rgb(var(--v-theme-grid));
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  list-style: none;
  margin: 0;
  padding: 0.25rem 0;
  /* Above SortAndLimitControl's dropdown (z-index: 98) */
  z-index: 99;
}

.language-filter__item {
  padding: 0.5rem 0.75rem;
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: 0.875rem;
  font-weight: 400;
  color: rgb(var(--v-theme-text));
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s ease;
}

.language-filter__item:hover {
  background-color: rgba(var(--v-theme-text), 0.06);
}

.language-filter__item--active {
  font-weight: 500;
  background-color: rgba(var(--v-theme-text), 0.06);
}

@media (max-width: 767px) {
  .language-filter {
    margin-inline-end: v-bind(LAYOUT.VIEW_PADDING_HORIZONTAL_MOBILE);
  }
}
</style>
