<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { parseLicenseId, type LicenseTerm } from '@/utils/license-utils'

const props = defineProps<{
  /** The source's own license text, shown when `licenseId` is not recognized */
  license: string
  licenseId?: string | null
}>()

const { t } = useI18n()

const parsed = computed(() => parseLicenseId(props.licenseId))

const termLabels: Record<LicenseTerm, () => string> = {
  by: () => t('licenses.termBy'),
  nc: () => t('licenses.termNc'),
  nd: () => t('licenses.termNd'),
  sa: () => t('licenses.termSa')
}

const name = computed(() => {
  const license = parsed.value
  if (!license) return props.license?.replace(/\.$/, '')
  if (license.kind === 'cc0') return t('licenses.cc0Name')

  const terms = license.terms.map((term) => termLabels[term]()).join(t('licenses.termSeparator'))
  return license.version
    ? t('licenses.ccName', { terms, version: license.version })
    : t('licenses.ccNameUnversioned', { terms })
})

// CC0 is already fully named, so only the other licenses get a short code
const code = computed(() => (parsed.value?.kind === 'cc' ? parsed.value.code : null))
</script>

<template>
  <div class="inter-13">
    <a
      v-if="parsed?.url"
      class="license-link text-decoration-underline"
      :href="parsed.url"
      target="_blank"
      rel="noopener noreferrer"
    >
      {{ name }} <span v-if="code" class="license-code">({{ code }})</span>
    </a>
    <template v-else>
      {{ name }} <span v-if="code" class="license-code">({{ code }})</span>
    </template>
  </div>
</template>

<style scoped>
.license-link {
  color: rgb(var(--v-theme-author));
}

.license-link:hover,
.license-link:focus {
  color: rgb(var(--v-theme-text));
}

/* Keep the short code in one piece when the name wraps in a narrow column */
.license-code {
  white-space: nowrap;
}
</style>
