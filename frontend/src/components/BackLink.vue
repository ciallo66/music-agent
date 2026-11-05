<!-- 页面内返回入口：详情/子页面左上角一个轻量按钮，和顶部搜索框同一套造型。
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
    <AppIcon name="arrow-left" :size="14" />
    <span>{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import AppIcon from './AppIcon.vue'

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
.back-link {
  display: inline-flex;
  height: 30px;
  align-items: center;
  gap: 6px;
  margin-bottom: 14px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  font-family: inherit;
  font-size: var(--fs-xs);
  cursor: pointer;
}
.back-link:hover {
  border-color: var(--border-strong);
  color: var(--text);
  background: var(--surface-hover);
}
.back-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
