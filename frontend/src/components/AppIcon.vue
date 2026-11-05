<!-- 统一线性图标：内联 SVG，不引入图标依赖，也不会出现 emoji 与字符图标的字重不一致。 -->
<template>
  <svg
    class="app-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="(path, index) in paths" :key="index" :d="path" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/** 图标名到 SVG path 的映射：24×24 画布，只描边不填充。 */
const ICONS: Record<string, string[]> = {
  home: ['M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z', 'M9 21v-6h6v6'],
  library: ['M5 4.5A1.5 1.5 0 0 1 6.5 3H19v18H6.5A1.5 1.5 0 0 1 5 19.5z', 'M9 3v18'],
  agent: ['M4 5h16v11H9l-5 4z'],
  list: ['M8 6h12M8 12h12M8 18h12', 'M4 6h.01M4 12h.01M4 18h.01'],
  heart: ['M12 20.3 4.9 13.2a4.7 4.7 0 0 1 6.6-6.7l.5.5.5-.5a4.7 4.7 0 0 1 6.6 6.7z'],
  chart: ['M4 20V4M4 20h16', 'M8 16v-4M12.5 16V8M17 16v-6'],
  search: ['M17.5 11a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0z', 'M16.2 16.2 20.5 20.5'],
  lock: ['M8 10V7.5a4 4 0 0 1 8 0V10', 'M5.5 10h13v9a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1z'],
  menu: ['M4 7h16M4 12h16M4 17h16'],
  close: ['M6 6l12 12M18 6 6 18'],
  plus: ['M12 5v14M5 12h14'],
  'arrow-right': ['M5 12h14M13 6l6 6-6 6'],
  'arrow-left': ['M19 12H5M11 6l-6 6 6 6'],
  check: ['M5 12.5 10 17.5 19 6.5'],
  alert: ['M12 4 3 20h18z', 'M12 10v4M12 17h.01'],
  refresh: ['M20 12a8 8 0 1 1-2.3-5.6', 'M20 4v5h-5'],
  music: [
    'M9 18V6l10-2v12',
    'M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    'M19 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
  ],
  external: [
    'M14 4h6v6',
    'M20 4 11 13',
    'M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5',
  ],
  user: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M4.5 21a7.5 7.5 0 0 1 15 0'],
  filter: ['M4 6h16M7 12h10M10 18h4'],
  info: ['M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z', 'M12 11v5M12 8h.01'],
  shield: ['M12 3l7 3v5.5c0 4.4-2.9 7.8-7 9.5-4.1-1.7-7-5.1-7-9.5V6z'],
  edit: ['M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z', 'M14.5 6.5 17.5 9.5'],
}

const props = withDefaults(
  defineProps<{
    /** 图标名，见 ICONS；未知名称渲染为空，不阻塞页面 */
    name: string
    /** 显示尺寸（px），默认 16 */
    size?: number
    /** 描边宽度，默认 1.6 */
    strokeWidth?: number
  }>(),
  { size: 16, strokeWidth: 1.6 },
)

const paths = computed(() => ICONS[props.name] ?? [])
</script>

<style scoped>
.app-icon {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: -0.15em;
}
</style>
