import { ref, computed, watch } from 'vue'

export function useInfiniteScroll<T>(
  items: () => T[],
  batchSize: number = 20,
  options: { resetOnItemsChange?: boolean } = {}
) {
  const displayedCount = ref(batchSize)

  const displayedItems = computed(() => items().slice(0, displayedCount.value))

  const hasMore = computed(() => displayedItems.value.length < items().length)

  function loadMore() {
    if (!hasMore.value) return
    displayedCount.value = Math.min(displayedCount.value + batchSize, items().length)
  }

  function reset() {
    displayedCount.value = batchSize
  }

  if (options.resetOnItemsChange ?? true) {
    watch(items, reset)
  }

  return {
    displayedItems,
    hasMore,
    loadMore,
    reset,
    displayedCount
  }
}
