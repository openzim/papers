<script setup lang="ts">
import {
  mdiAccountGroup,
  mdiAccountTie,
  mdiBookOpenPageVariant,
  mdiBookOpenVariant,
  mdiBookshelf,
  mdiBriefcase,
  mdiCalculatorVariant,
  mdiCodeBraces,
  mdiCog,
  mdiCompass,
  mdiDotsHorizontal,
  mdiEarth,
  mdiEmoticonHappyOutline,
  mdiFeather,
  mdiHeadLightbulb,
  mdiHeart,
  mdiHistory,
  mdiImageFilterHdr,
  mdiIncognito,
  mdiInformation,
  mdiLibrary,
  mdiMagicStaff,
  mdiMapMarker,
  mdiMicroscope,
  mdiNewspaperVariant,
  mdiPalette,
  mdiPencil,
  mdiRocketLaunch,
  mdiScaleBalance,
  mdiSchool,
  mdiStethoscope,
  mdiTeddyBear,
  mdiTheater,
  mdiTranslate,
  mdiTrophyVariant
} from '@mdi/js'

const props = defineProps<{
  subject: string | null
  fallback?: string
}>()

const OPEN_TEXTBOOK_SUBJECT_ICONS: Record<string, string> = {
  Business: mdiBriefcase,
  'Computer Science': mdiCodeBraces,
  Education: mdiSchool,
  'Engineering & Technology': mdiCog,
  Humanities: mdiTheater,
  'Journalism, Media Studies & Communications': mdiNewspaperVariant,
  Law: mdiScaleBalance,
  Mathematics: mdiCalculatorVariant,
  Medicine: mdiStethoscope,
  'Natural Sciences': mdiMicroscope,
  'Social Sciences': mdiAccountGroup,
  'Student Success': mdiTrophyVariant
}

const ONE_MORE_LIBRARY_CATEGORY_ICONS: Record<string, string> = {
  Arts: mdiPalette,
  Ciencias: mdiMicroscope,
  'Ciencias sociales': mdiAccountGroup,
  'Filosofia e Psicologia': mdiHeadLightbulb,
  'Filosofía y Psicología': mdiHeadLightbulb,
  'General works and Information': mdiInformation,
  'Grandes colecciones': mdiBookshelf,
  'Grandi collezioni': mdiBookshelf,
  'große Sammlungen': mdiBookshelf,
  'Histoire et Géographie': mdiEarth,
  'Historia y Geografía': mdiEarth,
  'History and Geography': mdiEarth,
  Language: mdiTranslate,
  Lenguaje: mdiTranslate,
  Letras: mdiBookshelf,
  Letteratura: mdiBookshelf,
  Literatur: mdiBookshelf,
  Literatura: mdiBookshelf,
  Literature: mdiBookshelf,
  Littérature: mdiBookshelf,
  'Major collections': mdiBookshelf,
  'Obras generales e información': mdiInformation,
  'Philosophie et Psychologie': mdiHeadLightbulb,
  'Philosophie und Psychologie': mdiHeadLightbulb,
  'Philosophy and Psychology': mdiHeadLightbulb,
  Religion: mdiLibrary,
  Religione: mdiLibrary,
  Religión: mdiLibrary,
  Réligion: mdiLibrary,
  Science: mdiMicroscope,
  Sciences: mdiMicroscope,
  'Sciences sociales': mdiAccountGroup,
  'Scienze sociali': mdiAccountGroup,
  'Social sciences': mdiAccountGroup,
  Sozialwissenschaften: mdiAccountGroup,
  Sprache: mdiTranslate,
  'Storia e Geografia': mdiEarth,
  Technology: mdiCog,
  Wissenschaft: mdiMicroscope,
  Литература: mdiBookshelf,
  'Социальные науки': mdiAccountGroup,
  الأدب: mdiBookshelf,
  'الفلسفة وعلم النفس': mdiHeadLightbulb
}

const BIBLIOTHEQUE_NUMERIQUE_ROMANDE_COLLECTION_ICONS: Record<string, string> = {
  Amour: mdiHeart,
  Art: mdiPalette,
  Autres: mdiDotsHorizontal,
  Aventure: mdiCompass,
  'Bande dessinée': mdiBookOpenPageVariant,
  'Biographie & Autobiographie': mdiAccountTie,
  Conte: mdiMagicStaff,
  'Essai & Chronique': mdiPencil,
  Historique: mdiHistory,
  Humour: mdiEmoticonHappyOutline,
  Jeunesse: mdiTeddyBear,
  Nouvelles: mdiNewspaperVariant,
  Philosophie: mdiHeadLightbulb,
  'Policier & Mystère': mdiIncognito,
  Poésie: mdiFeather,
  'Régions & terroir': mdiMapMarker,
  Roman: mdiBookOpenVariant,
  'Science-fiction & Fantastique': mdiRocketLaunch,
  Société: mdiAccountGroup,
  Théâtre: mdiTheater,
  'Voyage & Montagne': mdiImageFilterHdr
}

const SUBJECT_ICONS: Record<string, string> = {
  ...OPEN_TEXTBOOK_SUBJECT_ICONS,
  ...ONE_MORE_LIBRARY_CATEGORY_ICONS,
  ...BIBLIOTHEQUE_NUMERIQUE_ROMANDE_COLLECTION_ICONS
}

function getSubjectCollectionIcon(subject: string | null): string {
  return (subject && SUBJECT_ICONS[subject]) || props.fallback || mdiBookshelf
}
</script>

<template>
  <svg class="subject-icon" viewBox="0 0 24 24">
    <path :d="getSubjectCollectionIcon(subject)" />
  </svg>
</template>

<style scoped>
.subject-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: currentColor;
}
</style>
