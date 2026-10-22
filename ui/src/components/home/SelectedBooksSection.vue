<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import type { BookPreview } from '@/types'
import BooksGrid from '@/components/book/BooksGrid.vue'
import SectionHeader from '@/components/common/SectionHeader.vue'
import FireRating from '@/components/common/FireRating.vue'
import { useHasPopularity } from '@/composables/useHasPopularity'
import { TYPOGRAPHY, THEME_COLORS, LAYOUT } from '@/constants/theme'
import BookCoverImage from '@/components/common/BookCoverImage.vue'

const props = defineProps<{
  books: BookPreview[]
}>()

const { t } = useI18n()
const router = useRouter()
const hasPopularity = useHasPopularity()

const byTitle = (a: BookPreview, b: BookPreview) => a.title.localeCompare(b.title)
const byPopularity = (a: BookPreview, b: BookPreview) => b.popularity - a.popularity

const mostPopular = computed(() => {
  if (!hasPopularity.value || props.books.length === 0) return null
  return [...props.books].sort(byPopularity)[0]
})

const topBooks = computed(() => {
  const excludedId = mostPopular.value?.id
  const comparator = hasPopularity.value ? byPopularity : byTitle
  return [...props.books]
    .filter((b) => b.id !== excludedId)
    .sort(comparator)
    .slice(0, 8)
})

function goToBooks() {
  router.push('/books')
}

function goToBook(id: string) {
  router.push(`/book/${id}`)
}

function goToAuthor(id: string) {
  router.push(`/author/${id}`)
}
</script>

<template>
  <div class="selected-books-section">
    <div class="selected-books-section__inner">
      <section-header
        :title="t('home.selectedBooks')"
        :action-label="t('home.discoverAllBooks')"
        @action="goToBooks"
      />

      <div class="selected-books-section__grid">
        <div class="books-grid">
          <books-grid :books="topBooks" :columns="mostPopular ? 4 : 8" variant="compact" />
        </div>

        <div v-if="mostPopular" class="selected-books-section__featured">
          <div class="selected-books-section__featured-inner">
            <p class="featured-book__label">
              {{ t('home.mostPopular') }}
            </p>

            <button class="featured-book__cover-wrapper" @click="goToBook(mostPopular.id)">
              <book-cover-image
                :cover-path="mostPopular.coverPath"
                :alt="t('book.coverAlt', { title: mostPopular.title })"
                class="featured-book__cover"
                height="calc(450px - 3rem)"
              />
            </button>

            <button class="featured-book__title-button" @click="goToBook(mostPopular.id)">
              <h3 class="featured-book__title">
                {{ mostPopular.title }}
              </h3>
            </button>

            <button
              v-if="mostPopular.author"
              class="featured-book__author-button"
              @click="goToAuthor(mostPopular.author.id)"
            >
              <p class="featured-book__author">
                {{ mostPopular.author?.name }}
              </p>
            </button>

            <div class="featured-book__flames">
              <fire-rating :flames="mostPopular.flames" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.selected-books-section {
  max-width: v-bind(LAYOUT.MAX_CONTENT_WIDTH);
  margin-inline: auto;
  padding: 1.5rem 0;
}

.selected-books-section__grid {
  display: flex;
}

/* Fixed flex bases: with `auto`, the split depends on content size, which
   changes as lazy-loaded covers arrive */
.books-grid {
  flex: 1 1 0;
  min-width: 0;
}

.selected-books-section__featured {
  margin-top: v-bind(LAYOUT.BOOK_CARD_MARGIN);
  margin-inline-start: v-bind(LAYOUT.BOOK_CARD_MARGIN);
  flex: 0 0 30%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  position: relative;
}

.selected-books-section__featured-inner {
  padding: 3rem;
  background-color: rgb(var(--v-theme-focusBook));
  color: #ffffff;
  border-radius: 10px;
}

.featured-book__label {
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.BODY_SIZE);
  font-weight: bold;
  color: #ffffff;
  opacity: 0.9;
  margin: 0 0 1rem;
  text-align: start;
  width: 100%;
  padding: 0rem;
}

.featured-book__cover-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 0.15rem;
  width: 100%;
  aspect-ratio: 2 / 3;
  max-height: 450px;
  flex-shrink: 0;
  align-self: center;
  padding: 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
}

.featured-book__cover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4);
}

.featured-book__formats {
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.CAPTION_SIZE);
  font-weight: v-bind(TYPOGRAPHY.CAPTION_WEIGHT);
  color: v-bind(THEME_COLORS.FORMAT);
  margin: auto 0 0.5rem;
  text-align: start;
  width: 100%;
}

.featured-book__title-button,
.featured-book__author-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  text-align: start;
  width: 100%;
}

.featured-book__title-button {
  margin-bottom: 0.5rem;
}

.featured-book__author-button {
  margin-bottom: 0.75rem;
}

.featured-book__title {
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.H2_SIZE);
  font-weight: v-bind(TYPOGRAPHY.H2_WEIGHT);
  line-height: 1.3;
  color: #ffffff;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  text-align: start;
}

.featured-book__author {
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.BODY_SIZE);
  font-weight: v-bind(TYPOGRAPHY.BODY_WEIGHT);
  color: v-bind(THEME_COLORS.AUTHOR_FOCUS);
  margin: 0;
  text-align: start;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.featured-book__title-button:hover .featured-book__title,
.featured-book__author-button:hover .featured-book__author {
  text-decoration: underline;
}

.featured-book__flames {
  padding-top: 0.25rem;
  width: 100%;
  display: flex;
  justify-content: flex-start;
}

.featured-book__flames :deep(.flame-icon) {
  width: 22px;
  height: 22px;
}

@media (max-width: 767px) {
  .selected-books-section__grid {
    display: inline;
  }

  .selected-books-section__featured {
    padding-top: 4rem;
    margin-inline: auto;
  }
}
</style>
