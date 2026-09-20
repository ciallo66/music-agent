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
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  background: linear-gradient(145deg, var(--cover-from), var(--cover-to));
  color: var(--cover-text);
  user-select: none;
}
.cover-glyph {
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
}
/* 右下角来源角标：把「数据来自哪」变成设计的一部分 */
.cover-source {
  position: absolute;
  right: 4px;
  bottom: 3px;
  color: var(--cover-accent);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.06em;
  opacity: 0.85;
}
.size-sm {
  width: 44px;
  height: 44px;
  border-radius: 12px;
}
.size-sm .cover-glyph {
  font-size: 20px;
}
.size-md {
  width: 56px;
  height: 56px;
  border-radius: 14px;
}
.size-md .cover-glyph {
  font-size: 26px;
}
.size-lg {
  width: 112px;
  height: 112px;
  border-radius: 20px;
}
.size-lg .cover-glyph {
  font-size: 54px;
}
.size-lg .cover-source {
  right: 8px;
  bottom: 7px;
  font-size: 11px;
}
</style>
