// 延迟加载占位：请求足够快时不显示骨架，避免「骨架一闪就被内容替换」的闪烁。
// 用法：
//   const loading = ref(false)                       // 保留原有的加载标记
//   const showSkeleton = useDelayedFlag(loading)     // 模板里用 v-if="showSkeleton"
// 说明：超过 delay 毫秒仍在加载才显示占位；数据提前返回则整个加载态都不会出现，
// 页面直接从上一屏过渡到内容，不会有中间一次布局跳动。
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

export function useDelayedFlag(source: Ref<boolean>, delay = 150): Ref<boolean> {
  const visible = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  const clear = () => {
    if (timer === null) return
    clearTimeout(timer)
    timer = null
  }

  watch(
    source,
    (isLoading) => {
      clear()
      if (!isLoading) {
        visible.value = false
        return
      }
      timer = setTimeout(() => {
        timer = null
        visible.value = true
      }, delay)
    },
    { immediate: true },
  )

  onBeforeUnmount(clear)
  return visible
}
