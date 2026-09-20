<!-- 页面内返回入口：详情/子页面左上角一个胶囊按钮，和搜索框同一套造型。
     优先回退到上一页（保留了从内容库点进来的来路），没有历史时退回语义父级页面，
     直接贴链接打开也不会变成死按钮。 -->
<template>
  <button
    type="button"
    class="back-link"
    :title="`返回${label}`"
    :aria-label="`返回${label}`"
    @click="goBack"
  >
    <span class="back-arrow" aria-hidden="true">←</span>
    <span>{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'

const props = defineProps<{
  /** 按钮上显示的目标名，例如「内容库」 */
  label: string
  /** 没有可回退的历史时去哪（语义父级页面） */
  fallback: RouteLocationRaw
}>()

const router = useRouter()

// history.state.back 为 null 说明这是新标签页/直接粘贴进来的第一个页面，
// 此时 router.back() 会退出站点，必须走 fallback。
const canGoBack = computed(() => window.history.state?.back != null)

function goBack(): void {
  if (canGoBack.value) {
    router.back()
    return
  }
  void router.push(props.fallback)
}
</script>

<style scoped>
/* 与顶栏搜索框同款造型：深底、细边框、悬停高亮，尺寸略小一档 */
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 14px;
  padding: 7px 13px 7px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.045);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    background 0.15s ease,
    transform 0.15s ease;
}
.back-link:hover {
  border-color: rgba(110, 231, 210, 0.55);
  color: var(--text);
  background: var(--surface-hover);
  transform: translateX(-2px);
}
.back-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.back-arrow {
  font-size: 14px;
  line-height: 1;
}
</style>
