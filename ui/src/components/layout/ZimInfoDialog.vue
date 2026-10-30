<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDisplay, useTheme } from 'vuetify'
import { useMainStore } from '@/stores/main'
import { useFormatters } from '@/composables/useFormatters'
import { getCollectionLabel } from '@/utils/collection-names'
import { formatScrapeDate } from '@/utils/format-utils'
import { TYPOGRAPHY } from '@/constants/theme'
import { usePlural } from '@/plugins/i18n'

const ZIM_INFO_TEXT_LIGHT = '#38495c'
const ZIM_INFO_BGD_DARK = '#38495c'
const ZIM_INFO_TEXT_DARK = '#ffffff'
const ZIM_INFO_SCRIM = '#3c485acc'
const ZIM_INFO_SCRIM_DARK = '#121d28cc'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const { t, locale } = useI18n()
const { tp } = usePlural()
const main = useMainStore()
const theme = useTheme()
const { mobile } = useDisplay()
const { formatLanguages, formatLabel } = useFormatters()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

// v-dialog teleports its content to <body>, outside this component's root
// element where Vue sets the CSS variables of `v-bind()` in <style>, so these
// are set directly on the card instead
const typographyVars = computed(() => ({
  '--zim-info-font-family': TYPOGRAPHY.FONT_FAMILY,
  '--zim-info-title-size': mobile.value ? TYPOGRAPHY.H2_SIZE_MOBILE : TYPOGRAPHY.H2_SIZE,
  '--zim-info-row-size': mobile.value ? TYPOGRAPHY.SMALL_SIZE_MOBILE : TYPOGRAPHY.SMALL_SIZE,
  '--zim-info-bold-weight': TYPOGRAPHY.H2_WEIGHT
}))

const cardStyle = computed(() => ({
  ...typographyVars.value,
  ...(theme.global.current.value.dark
    ? { backgroundColor: ZIM_INFO_BGD_DARK, color: ZIM_INFO_TEXT_DARK }
    : { color: ZIM_INFO_TEXT_LIGHT })
}))

const scrimColor = computed(() =>
  theme.global.current.value.dark ? ZIM_INFO_SCRIM_DARK : ZIM_INFO_SCRIM
)

const contentInfo = computed(() => main.config?.contentInfo)

interface InfoRow {
  label: string
  values: string[] | null
  mode: 'list' | 'csv'
}

// Labels are pluralized on the number of values; no values means "all"
function valuesCount(values: string[] | null) {
  return values?.length || null
}

const rows = computed<InfoRow[]>(() => {
  const collections =
    contentInfo.value?.collections?.map((value) => getCollectionLabel(value, t)) ?? null
  const books = contentInfo.value?.books ?? null
  const languages = contentInfo.value?.languages?.map((code) => formatLanguages([code])) ?? null
  const formats = contentInfo.value?.formats?.map((format) => formatLabel(format)) ?? null
  return [
    {
      label: tp('zimInfo.collections', valuesCount(collections)),
      values: collections,
      mode: 'list'
    },
    { label: tp('zimInfo.books', valuesCount(books)), values: books, mode: 'list' },
    { label: tp('zimInfo.language', valuesCount(languages)), values: languages, mode: 'list' },
    { label: tp('zimInfo.formats', valuesCount(formats)), values: formats, mode: 'csv' }
  ]
})

const dateScrapedValue = computed(() => {
  const isoDate = contentInfo.value?.dateScraped
  return isoDate ? formatScrapeDate(isoDate, locale.value) : ''
})
</script>

<template>
  <v-dialog v-model="isOpen" max-width="480" :scrim="scrimColor">
    <v-card :style="cardStyle" class="zim-info-dialog__card">
      <v-btn
        class="zim-info-dialog__close"
        icon="mdi-close"
        variant="text"
        density="compact"
        size="small"
        elevation="0"
        :aria-label="t('common.close')"
        @click="isOpen = false"
      />
      <v-card-title class="zim-info-dialog__title">
        {{ t('zimInfo.title') }}
      </v-card-title>
      <v-card-text>
        <dl class="zim-info-dialog__list">
          <div class="zim-info-dialog__row">
            <dt>{{ t('zimInfo.source') }}</dt>
            <dd>{{ contentInfo?.source }}</dd>
          </div>
          <div v-for="row in rows" :key="row.label" class="zim-info-dialog__row">
            <dt>{{ row.label }}</dt>
            <dd>
              <template v-if="!row.values?.length">{{ t('common.all') }}</template>
              <template v-else-if="row.mode === 'csv'">{{ row.values.join(', ') }}</template>
              <template v-else-if="row.values.length === 1">{{ row.values[0] }}</template>
              <ul v-else class="zim-info-dialog__bullets">
                <li v-for="value in row.values" :key="value">{{ value }}</li>
              </ul>
            </dd>
          </div>
          <div class="zim-info-dialog__row">
            <dt>{{ t('zimInfo.dateScraped') }}</dt>
            <dd>{{ dateScrapedValue }}</dd>
          </div>
        </dl>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.zim-info-dialog__card {
  position: relative;
  font-family: var(--zim-info-font-family);
  padding: 2rem;
}

/* Positioned against the card, independently of the title box model */
.zim-info-dialog__close {
  position: absolute;
  top: 0.75rem;
  inset-inline-end: 0.75rem;
  z-index: 1;
}

.zim-info-dialog__title {
  /* Keep a long title from running under the close button */
  padding-inline-end: 3rem;
  font-family: var(--zim-info-font-family);
  font-size: var(--zim-info-title-size);
  font-weight: var(--zim-info-bold-weight);
}

.zim-info-dialog__list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding-top: 1rem;
  padding-bottom: 2rem;
}

.zim-info-dialog__row {
  display: grid;
  grid-template-columns: 9rem 1fr;
  gap: 0.75rem;
  font-family: var(--zim-info-font-family);
  font-size: var(--zim-info-row-size);
  padding: 0.5rem 0;
  border-bottom: 1px dashed currentColor;
  /* Fainter separator, on browsers supporting color-mix() */
  border-bottom-color: color-mix(in srgb, currentColor 30%, transparent);
}

.zim-info-dialog__row:last-child {
  border-bottom: none;
}

.zim-info-dialog__row dt {
  font-weight: var(--zim-info-bold-weight);
}

.zim-info-dialog__row dd {
  margin: 0;
}

.zim-info-dialog__bullets {
  margin: 0;
  padding-inline-start: 0.8rem;
  list-style: none;
}

.zim-info-dialog__bullets li {
  position: relative;
}

.zim-info-dialog__bullets li::before {
  content: '–';
  position: absolute;
  inset-inline-start: -0.8rem;
}

@media (max-width: 767px) {
  .zim-info-dialog__card {
    padding: 1rem;
  }

  .zim-info-dialog__list {
    padding-top: 0.5rem;
    padding-bottom: 1rem;
  }

  .zim-info-dialog__row {
    grid-template-columns: 1fr;
    gap: 0.15rem;
  }
}

:deep(.v-overlay__scrim) {
  opacity: 0.8 !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
</style>
