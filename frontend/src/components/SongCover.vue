<!-- 排版封面：用歌名首字 + 流派/节拍派生的配色，替代缺失的专辑图。
     同一首歌在任何页面（列表 / 详情 / 推荐卡 / 歌单 / 最近播放）算出的配色完全一致，
     因为它只依赖列表与详情接口都返回的字段（genre、bpm、danceability）。 -->
<template>
  <span
    class="song-cover"
    :class="[`size-${size}`, { 'with-source': showSource && badge !== '' }]"
    :style="style"
    :title="label"
    aria-hidden="true"
  >
    <span class="cover-glyph">{{ glyph }}</span>
    <small v-if="showSource && badge" class="cover-source">{{ badge }}</small>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { coverGlyph, coverPalette, sourceBadge } from '../utils/cover'

const props = withDefaults(
  defineProps<{
    song: {
      id: number
      title: string
      genre?: string | null
      bpm?: number | null
      danceability?: number | null
      source?: string | null
    }
    /** 尺寸：sm 列表、md 详情/卡片、lg 详情页大图 */
    size?: 'sm' | 'md' | 'lg'
    /** 是否在右下角显示数据来源角标（列表里太挤，默认不显示） */
    showSource?: boolean
  }>(),
  { size: 'sm', showSource: false },
)

const palette = computed(() => coverPalette(props.song))
const glyph = computed(() => coverGlyph(props.song.title))
const badge = computed(() => sourceBadge(props.song.source))
const style = computed(() => ({
  '--cover-from': palette.value.from,
  '--cover-to': palette.value.to,
  '--cover-text': palette.value.text,
  '--cover-accent': palette.value.accent,
}))
// 无障碍：封面是装饰，但读屏时给一个能说明它是什么的标签
const label = computed(
  () => `封面：${props.song.title.slice(0, 1)}｜${props.song.genre ?? '未知风格'}`,
)
</script>

<style scoped>
.song-cover {
  position: relative;
  display: grid;
  flex-shrink: 0;
  place-items: center;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm);
  background: linear-gradient(145deg, var(--cover-from), var(--cover-to));
  color: var(--cover-text);
  user-select: none;
}
.cover-glyph {
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1;
}
/* 右下角来源角标：把「数据来自哪」变成设计的一部分 */
.cover-source {
  position: absolute;
  right: 4px;
  bottom: 3px;
  color: var(--cover-accent);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  opacity: 0.8;
}
.size-sm {
  width: 40px;
  height: 40px;
}
.size-sm .cover-glyph {
  font-size: 17px;
}
.size-md {
  width: 52px;
  height: 52px;
}
.size-md .cover-glyph {
  font-size: 22px;
}
.size-lg {
  width: 96px;
  height: 96px;
}
.size-lg .cover-glyph {
  font-size: 42px;
}
.size-lg .cover-source {
  right: 7px;
  bottom: 6px;
  font-size: 11px;
}
</style>
