<script setup lang="ts">
/**
 * LanguageSwitcher — translate-icon trigger opening a searchable list of
 * interface languages.
 *
 * Deliberately NOT built on Vuetify's `v-menu`/`v-autocomplete`: nesting a
 * select-like overlay inside another overlay is exactly the pattern this
 * project's `vite.config.ts` already documents as unreliable (z-index
 * stacking across the two), and `v-autocomplete`'s virtualized list doesn't
 * render reliably in every environment either. A plain positioned panel with
 * a manual click-outside listener - the same pattern already used by
 * `SortAndLimitControl.vue` - avoids both issues.
 */
import { ref, computed, nextTick, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { setCurrentLocale, supportedLanguages } from '@/plugins/i18n'
import {
  buildLanguageSwitcherItems,
  filterLanguageItems,
  isDivider,
  type LanguageItem,
  type LanguageListEntry
} from '@/utils/language-switcher-items'
import { useMainStore } from '@/stores/main'

const { t } = useI18n()
const main = useMainStore()

const open = ref(false)
const query = ref('')
const searchInput = ref<HTMLInputElement | null>(null)

const items = computed(() => buildLanguageSwitcherItems(main.config?.bookLanguages))

const displayedItems = computed<LanguageListEntry[]>(() =>
  query.value.trim() ? filterLanguageItems(items.value, query.value) : items.value
)

function toggle() {
  open.value = !open.value
  if (open.value) {
    query.value = ''
    nextTick(() => searchInput.value?.focus())
  }
}

function selectLanguage(entry: LanguageItem) {
  const language = supportedLanguages.find((lang) => lang.code === entry.code)
  if (!language) return
  setCurrentLocale(language)
  open.value = false
}

function closeOnOutsideClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.language-switcher')) {
    open.value = false
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('click', closeOnOutsideClick)
  onUnmounted(() => document.removeEventListener('click', closeOnOutsideClick))
}
</script>

<template>
  <div class="language-switcher">
    <button
      class="language-switcher__trigger"
      type="button"
      :aria-label="t('common.changeInterfaceLanguage')"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click.stop="toggle"
    >
      <v-icon icon="mdi-translate" size="20" />
    </button>

    <div v-if="open" class="language-switcher__menu">
      <input
        ref="searchInput"
        v-model="query"
        type="text"
        class="language-switcher__search"
        :placeholder="t('common.selectInterfaceLanguage')"
        :aria-label="t('common.selectInterfaceLanguage')"
        @keyup.escape="open = false"
      />
      <ul class="language-switcher__list" role="listbox">
        <template v-for="entry in displayedItems" :key="entry.id">
          <li v-if="isDivider(entry)" class="language-switcher__divider" role="separator" />
          <li v-else class="language-switcher__item" role="option" @click="selectLanguage(entry)">
            {{ entry.title }}
          </li>
        </template>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.language-switcher {
  position: relative;
}

.language-switcher__trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: none;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: rgb(var(--v-theme-text));
  opacity: 0.65;
  transition:
    background-color 0.2s ease,
    opacity 0.2s ease;
}

.language-switcher__trigger:hover {
  opacity: 1;
  background-color: rgba(var(--v-theme-text), 0.06);
}

.language-switcher__menu {
  position: absolute;
  top: calc(100% + 4px);
  inset-inline-end: 0;
  width: 280px;
  display: flex;
  flex-direction: column;
  background: rgb(var(--v-theme-background));
  border: 1px solid rgb(var(--v-theme-grid));
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
  overflow: hidden;
}

.language-switcher__search {
  margin: 0.5rem;
  padding: 0.375rem 0.5rem;
  border: 1px solid rgb(var(--v-theme-grid));
  border-radius: 4px;
  background: rgb(var(--v-theme-background));
  color: rgb(var(--v-theme-text));
  font-size: 0.875rem;
}

.language-switcher__search:focus {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -1px;
}

.language-switcher__list {
  list-style: none;
  margin: 0;
  padding: 0.25rem 0;
  max-height: 320px;
  overflow-y: auto;
}

.language-switcher__divider {
  height: 1px;
  margin: 0.25rem 0;
  background: rgb(var(--v-theme-grid));
}

.language-switcher__item {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: rgb(var(--v-theme-text));
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background-color 0.2s ease;
}

.language-switcher__item:hover {
  background-color: rgba(var(--v-theme-text), 0.06);
}
</style>
