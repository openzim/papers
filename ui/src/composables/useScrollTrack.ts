import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { useRtl } from 'vuetify'

export interface UseScrollTrackOptions {
  cellSelector: string
  trackRef?: Ref<HTMLElement | null>
}

export function useScrollTrack(options: UseScrollTrackOptions) {
  const { isRtl } = useRtl()
  const trackRef = options.trackRef ?? ref<HTMLElement | null>(null)
  const hasPrevious = ref(false)
  const hasNext = ref(false)

  function updateScrollState() {
    const track = trackRef.value
    if (!track) return
    const maxScroll = track.scrollWidth - track.clientWidth
    const scrollFromStart = isRtl.value ? Math.abs(track.scrollLeft) : track.scrollLeft
    hasPrevious.value = scrollFromStart > 1
    hasNext.value = scrollFromStart < maxScroll - 1
  }

  function scrollByCell(direction: 1 | -1) {
    const track = trackRef.value
    if (!track) return
    const cell = track.querySelector(options.cellSelector)
    const cellWidth = cell ? cell.clientWidth : track.clientWidth / 5
    const scrollSign = isRtl.value ? -1 : 1
    track.scrollBy({ left: direction * scrollSign * cellWidth, behavior: 'smooth' })
  }

  function shiftPrevious() {
    scrollByCell(-1)
  }

  function shiftNext() {
    scrollByCell(1)
  }

  onMounted(() => {
    updateScrollState()
    window.addEventListener('resize', updateScrollState)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', updateScrollState)
  })

  return {
    trackRef,
    hasPrevious,
    hasNext,
    updateScrollState,
    scrollByCell,
    shiftPrevious,
    shiftNext
  }
}
