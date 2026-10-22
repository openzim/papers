<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AuthorPreview, AuthorDetail } from '@/types'
import AuthorCard from './AuthorCard.vue'
import CarouselArrow from '@/components/common/CarouselArrow.vue'
import { compareAuthorNames } from '@/utils/format-utils'
import { useDisplay } from 'vuetify'
import { useRouter } from 'vue-router'

const { mobile } = useDisplay()
const router = useRouter()

const props = defineProps<{
  authors: AuthorPreview[]
  currentAuthor: AuthorDetail
}>()

const { t } = useI18n()

const sortedAuthors = computed(() => [...props.authors].sort((a, b) => compareAuthorNames(a, b)))

const currentIndex = computed(() =>
  sortedAuthors.value.findIndex((a) => a.id === props.currentAuthor.id)
)

const hasPrevious = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < props.authors.length - 1)

function shiftLeft() {
  router.push(`/author/${sortedAuthors.value[currentIndex.value - 1].id}`)
}

function shiftRight() {
  router.push(`/author/${sortedAuthors.value[currentIndex.value + 1].id}`)
}
</script>

<template>
  <div class="author-details">
    <div class="author-arrow" v-if="!mobile">
      <carousel-arrow
        direction="prev"
        :disabled="!hasPrevious"
        :ariaLabel="t('common.previous')"
        @click="shiftLeft"
      />
    </div>

    <author-card :author="currentAuthor" variant="detailed" selected :navigate="false" />

    <div class="author-arrow" v-if="!mobile">
      <carousel-arrow
        direction="next"
        :disabled="!hasNext"
        :ariaLabel="t('common.next')"
        @click="shiftRight"
      />
    </div>
  </div>
</template>

<style scoped>
.author-details {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  padding-bottom: 3rem;
}

.author-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
