import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { useRtl } from 'vuetify'

const SCROLL_EDGE_TOLERANCE = 1

export interface UseScrollTrackOptions {
  cellSelector: string
  trackRef?: Ref<HTMLElement | null>
}

export function useScrollTrack(options: UseScrollTrackOptions) {
  const { isRtl } = useRtl()
  const trackRef = options.trackRef ?? ref<HTMLElement | null>(null)
  const hasPrevious = ref(false)
  const hasNext = ref(false)

  let scrollSign: 1 | -1 | 0 = 0

  function edges(track: HTMLElement) {
    const trackRect = track.getBoundingClientRect()
    let contentLeft = trackRect.left
    let contentRight = trackRect.right
    for (const child of Array.from(track.children)) {
      const childRect = child.getBoundingClientRect()
      if (childRect.width === 0) continue
      contentLeft = Math.min(contentLeft, childRect.left)
      contentRight = Math.max(contentRight, childRect.right)
    }
    const overflowLeft = trackRect.left - contentLeft
    const overflowRight = contentRight - trackRect.right
    return {
      trackRect,
      hiddenAtEnd: isRtl.value ? overflowLeft : overflowRight,
      hiddenAtStart: isRtl.value ? overflowRight : overflowLeft
    }
  }

  function updateScrollState() {
    const track = trackRef.value
    if (!track) return
    const { hiddenAtStart, hiddenAtEnd } = edges(track)
    hasPrevious.value = hiddenAtStart > SCROLL_EDGE_TOLERANCE
    hasNext.value = hiddenAtEnd > SCROLL_EDGE_TOLERANCE
  }

  function resolveScrollSign(track: HTMLElement, probe: number): 1 | -1 {
    if (scrollSign !== 0) return scrollSign
    const { hiddenAtEnd } = edges(track)
    const before = track.scrollLeft
    for (const delta of [probe, -probe]) {
      track.scrollLeft = before + delta
      const accepted = track.scrollLeft - before
      const reduced = hiddenAtEnd - edges(track).hiddenAtEnd
      track.scrollLeft = before
      if (accepted !== 0 && reduced !== 0) {
        scrollSign = accepted > 0 === reduced > 0 ? 1 : -1
        return scrollSign
      }
    }
    return isRtl.value ? -1 : 1
  }

  function scrollByCell(direction: 1 | -1) {
    const track = trackRef.value
    if (!track) return
    const cell = track.querySelector(options.cellSelector)
    const cellWidth = cell ? cell.clientWidth : track.clientWidth / 5
    track.scrollBy({
      left: direction * resolveScrollSign(track, cellWidth) * cellWidth,
      behavior: 'smooth'
    })
  }

  function distanceToStart() {
    const track = trackRef.value
    return track ? edges(track).hiddenAtStart : 0
  }

  function distanceToEnd() {
    const track = trackRef.value
    return track ? edges(track).hiddenAtEnd : 0
  }

  function distanceOf(cell: Element) {
    const track = trackRef.value
    if (!track) return 0
    const { trackRect } = edges(track)
    const cellRect = cell.getBoundingClientRect()
    return isRtl.value ? trackRect.right - cellRect.right : cellRect.left - trackRect.left
  }

  function alignCell(cell: Element, targetDistance = 0) {
    const track = trackRef.value
    if (!track) return
    const delta = distanceOf(cell) - targetDistance
    if (Math.abs(delta) <= SCROLL_EDGE_TOLERANCE) return
    track.scrollBy({
      left: resolveScrollSign(track, Math.abs(delta)) * delta,
      behavior: 'instant'
    })
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
    alignCell,
    distanceOf,
    distanceToStart,
    distanceToEnd,
    shiftPrevious,
    shiftNext
  }
}
