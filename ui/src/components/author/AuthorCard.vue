<script setup lang="ts">
import { computed } from 'vue'
import type { AuthorDetail, AuthorPreview } from '@/types'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { useDisplay } from 'vuetify'
import AuthorAvatar from './AuthorAvatar.vue'
import { LAYOUT, TYPOGRAPHY } from '@/constants/theme'

/*
 * Variants:
 * - tile: large avatar above the name, unboxed (authors grid)
 * - mini: small avatar above the name, boxed
 * - row: medium avatar beside the name, boxed
 * - detailed: like row, plus the author bio and source link
 */
interface BaseProps {
  navigate?: boolean
  selected?: boolean
}

type Props = BaseProps &
  (
    | { author: AuthorDetail; variant: 'detailed' }
    | { author: AuthorPreview; variant?: 'mini' | 'row' | 'tile' }
  )

const props = withDefaults(defineProps<Props>(), {
  variant: 'mini',
  navigate: true,
  selected: false
})

const { t } = useI18n()
const { mobile } = useDisplay()

const avatarSize = computed(() => {
  switch (props.variant) {
    case 'mini':
      return 'small'
    case 'tile':
      return 'xlarge'
    default:
      return mobile.value ? 'medium' : 'large'
  }
})
</script>

<template>
  <component
    :is="navigate ? RouterLink : 'div'"
    :to="navigate ? `/author/${author.id}` : undefined"
    :aria-label="
      t('author.viewAuthor', {
        bookCount: t('author.bookCount', author.bookCount),
        name: author.displayName
      })
    "
    :class="[
      'author-card',
      'text-decoration-none',
      `author-card--${variant}`,
      {
        'author-card--boxed': variant !== 'tile',
        'author-card--selected': selected,
        'author-card__navigate': navigate
      }
    ]"
  >
    <div class="author-card__avatar-infos">
      <author-avatar
        :portrait-path="author.portraitPath"
        :name="author.displayName"
        :size="avatarSize"
        class="author-card__avatar"
      />

      <div class="author-card__infos">
        <h2 class="author-card__name">
          {{ author.displayName }}
        </h2>

        <p class="author-card__count">
          {{ t('author.bookCount', author.bookCount) }}
        </p>
      </div>
    </div>
    <div v-if="variant === 'detailed'" class="author-card__about">
      <p v-if="author.bio" class="author-card__bio">{{ author.bio }}</p>
      <a
        v-if="author.webpageResource"
        class="author-card__source"
        :href="author.webpageResource"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ t('author.wikipediaSource') }}
      </a>
    </div>
  </component>
</template>

<style scoped>
.author-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  width: 100%;
  color: rgb(var(--v-theme-text));
}

.author-card__avatar-infos {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.author-card--detailed .author-card__avatar-infos,
.author-card--row .author-card__avatar-infos {
  flex-direction: row;
  gap: 1rem;
}

.author-card--boxed {
  /* Fill the parent cell (minus margin); cells are flex rows */
  width: auto;
  flex: 1 1 auto;
  min-width: 0;
  margin: v-bind(LAYOUT.BOOK_CARD_MARGIN);
  /* Transparent border keeps the card size constant when it shows on hover */
  border: v-bind(LAYOUT.BOOK_CARD_HOVER_BORDER) solid transparent;
  border-radius: v-bind(LAYOUT.BOOK_CARD_RADIUS);
  background-color: rgb(var(--v-theme-cardBgd));
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;
}

.author-card--boxed.author-card--selected {
  background-color: rgb(var(--v-theme-cardBgdHover));
  border-color: rgb(var(--v-theme-cardBorderHover));
}

.author-card--boxed.author-card__navigate:hover,
.author-card--boxed.author-card__navigate:focus-visible {
  box-shadow: 0 0 10px 0 rgb(var(--v-theme-grid));
}

.author-card--detailed {
  flex-direction: row;
  gap: 2rem;
  min-height: 10rem;
}

.author-card--tile {
  height: 17rem;
}

.author-card__infos {
  display: flex;
  flex-direction: column;
  flex: 1 1 100%;
}

.author-card--row {
  align-items: start;
}

.author-card--row .author-card__infos,
.author-card--detailed .author-card__infos {
  align-items: start;
}

.author-card--detailed .author-card__infos {
  max-width: 14rem;
}

.author-card--tile .author-card__avatar,
.author-card--mini .author-card__avatar {
  margin-bottom: 1rem;
}

.author-card__avatar {
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease;
}

.author-card__name {
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-weight: v-bind(TYPOGRAPHY.H3_WEIGHT);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  text-align: start;
}

.author-card--row .author-card__name,
.author-card--detailed .author-card__name {
  font-size: v-bind(TYPOGRAPHY.H2_SIZE);
  margin-bottom: 0.5rem;
}

.author-card--mini .author-card__name,
.author-card--tile .author-card__name {
  font-size: v-bind(TYPOGRAPHY.H3_SIZE);
  margin-bottom: 0.25rem;
  text-align: center;
}

/* Always reserve two lines so avatars line up across consecutive cards */
.author-card--mini .author-card__name {
  min-height: calc(2em * 1.4);
}

/* Reserve room for a two-line name plus the book count, keeping both
   together, so avatars line up across consecutive cards */
.author-card--tile .author-card__infos {
  min-height: calc(
    2 * 1.4 * v-bind(TYPOGRAPHY.H3_SIZE) + 0.25rem + 1.4 * v-bind(TYPOGRAPHY.CAPTION_SIZE)
  );
}

.author-card__count {
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.CAPTION_SIZE);
  font-weight: v-bind(TYPOGRAPHY.CAPTION_WEIGHT);
  line-height: 1.4;
  color: rgb(var(--v-theme-text));
  opacity: 0.6;
  margin: 0;
  text-align: center;
}

.author-card__about {
  font-family: v-bind(TYPOGRAPHY.FONT_FAMILY);
  font-size: v-bind(TYPOGRAPHY.SMALL_SIZE);
  flex: 1 1;
}

.author-card__bio {
  padding-bottom: 1rem;
}

@media (max-width: 767px) {
  .author-card__about {
    font-size: v-bind(TYPOGRAPHY.SMALL_SIZE_MOBILE);
  }

  .author-card--detailed {
    flex-direction: column;
    align-items: start;
    gap: 1rem;
  }

  .author-card--detailed .author-card__infos {
    max-width: 100%;
  }
  .author-card--row .author-card__name,
  .author-card--detailed .author-card__name {
    font-size: v-bind(TYPOGRAPHY.H2_SIZE_MOBILE);
  }
}
</style>
