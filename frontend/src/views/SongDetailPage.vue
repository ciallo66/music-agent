<template>
  <div class="detail-page" v-if="song">
    <div class="song-header">
      <div class="cover-placeholder">{{ song.title.slice(0, 1) }}</div>
      <div class="info">
        <h2>{{ song.title }}</h2>
        <p class="artist">{{ song.artist.name }}</p>
        <p class="meta">
          {{ song.genre }} · {{ song.language }} ·
          {{ song.bpm ? Math.round(song.bpm) + ' BPM' : '' }}
        </p>
        <div class="actions">
          <el-button type="primary" @click="playSong">▶ 播放</el-button>
          <el-button @click="toggleFav">{{ isFav ? '已收藏' : '收藏' }}</el-button>
        </div>
      </div>
    </div>
    <div class="features" v-if="song.energy !== null">
      <h3>音乐特征</h3>
      <div class="feature-grid">
        <div class="feat-item">
          <span class="feat-label">BPM</span
          ><span class="feat-val">{{ song.bpm ? Math.round(song.bpm) : '-' }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">Key</span
          ><span class="feat-val">{{ song.music_key || '-' }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">Energy</span
          ><span class="feat-val">{{
            song.energy !== null ? (song.energy * 100).toFixed(0) + '%' : '-'
          }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">Valence</span
          ><span class="feat-val">{{
            song.valence !== null ? (song.valence * 100).toFixed(0) + '%' : '-'
          }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">Dance</span
          ><span class="feat-val">{{
            song.danceability !== null ? (song.danceability * 100).toFixed(0) + '%' : '-'
          }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">Loudness</span
          ><span class="feat-val">{{
            song.loudness !== null ? song.loudness.toFixed(1) + ' dB' : '-'
          }}</span>
        </div>
      </div>
    </div>
    <div class="radar-block" v-if="song.energy !== null">
      <h3>特征画像</h3>
      <div ref="chartEl" class="radar-chart"></div>
      <p class="radar-note">数值已归一化到 0-100（Loudness 按 -60~0 dB、BPM 按 0~180 归一化）</p>
    </div>
    <div class="detail-block" v-if="song.instruments">
      <h3>乐器</h3>
      <div class="tag-list">
        <span v-for="inst in instruments" :key="inst" class="tag">{{ inst }}</span>
      </div>
    </div>
    <div class="detail-block" v-if="song.song_structure">
      <h3>歌曲结构</h3>
      <p class="structure-text">{{ song.song_structure }}</p>
    </div>
    <div class="lyrics-section" v-if="song.lyrics">
      <h3>歌词</h3>
      <div v-if="lyricLines.length" class="lyrics-list">
        <button
          v-for="(line, index) in lyricLines"
          :key="`${line.time}-${index}`"
          class="lyric-line"
          :class="{ active: activeLyricIndex === index }"
          type="button"
          @click="seekLyric(line.time)"
        >
          {{ line.text }}
        </button>
      </div>
      <pre v-else class="lyrics-text">{{ song.lyrics }}</pre>
    </div>
  </div>
  <div v-else class="loading">加载中...</div>
</template>
<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getSong, type SongDetail } from '../api/songs'
import { addFavorite, listFavorites, removeFavorite } from '../api/favorites'
import { usePlayerStore } from '../stores/player'
import { showError, showSuccess } from '../utils/feedback'
import { parseLrc } from '../utils/lyrics'

echarts.use([RadarChart, TooltipComponent, LegendComponent, CanvasRenderer])

const route = useRoute()
const player = usePlayerStore()
const song = ref<SongDetail | null>(null)
const isFav = ref(false)
const chartEl = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const instruments = computed(() =>
  (song.value?.instruments ?? '')
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean),
)

const lyricLines = computed(() => parseLrc(song.value?.lyrics ?? ''))
const activeLyricIndex = computed(() => {
  if (!song.value || player.currentSong?.id !== song.value.id || lyricLines.value.length === 0) {
    return -1
  }
  let activeIndex = -1
  lyricLines.value.forEach((line, index) => {
    if (line.time <= player.currentTime) activeIndex = index
  })
  return activeIndex
})

async function load() {
  try {
    const { data } = await getSong(Number(route.params.id))
    song.value = data
  } catch (error) {
    showError(error, '歌曲详情加载失败')
    return
  }
  await nextTick()
  renderRadar()
  try {
    const { data: favData } = await listFavorites()
    const found = favData.items.find((item) => item.song_id === song.value?.id)
    if (found) isFav.value = true
  } catch {
    // 收藏状态接口暂不可用时保持未收藏，不影响详情与特征展示
  }
}

function normalizeLoudness(value: number | null) {
  if (value === null) return 0
  return Math.min(100, Math.max(0, ((value + 60) / 60) * 100))
}

function normalizeBpm(value: number | null) {
  if (value === null) return 0
  return Math.min(100, (value / 180) * 100)
}

function cssVariable(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function renderRadar() {
  if (!song.value || !chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const current = song.value
  const values = [
    current.energy !== null ? Math.round(current.energy * 100) : 0,
    current.valence !== null ? Math.round(current.valence * 100) : 0,
    current.danceability !== null ? Math.round(current.danceability * 100) : 0,
    Math.round(normalizeLoudness(current.loudness)),
    Math.round(normalizeBpm(current.bpm)),
  ]
  const textSecondary = cssVariable('--text-secondary')
  const chartBorder = cssVariable('--chart-border')
  const chartBorderStrong = cssVariable('--chart-border-strong')
  const chartAccentSoft = cssVariable('--chart-accent-soft')
  const chartAccentFill = cssVariable('--chart-accent-fill')
  const accent = cssVariable('--accent')
  chart.setOption({
    tooltip: {},
    legend: { show: false },
    radar: {
      indicator: [
        { name: 'Energy', max: 100 },
        { name: 'Valence', max: 100 },
        { name: 'Danceability', max: 100 },
        { name: 'Loudness', max: 100 },
        { name: 'BPM', max: 100 },
      ],
      radius: '68%',
      axisName: { color: textSecondary, fontSize: 12 },
      splitLine: { lineStyle: { color: chartBorder } },
      splitArea: {
        areaStyle: { color: [chartAccentSoft, chartAccentFill] },
      },
      axisLine: { lineStyle: { color: chartBorderStrong } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: current.title,
            symbol: 'circle',
            symbolSize: 4,
            lineStyle: { color: accent, width: 2 },
            itemStyle: { color: accent },
            areaStyle: { color: chartAccentFill },
          },
        ],
      },
    ],
  })
}

function onResize() {
  chart?.resize()
}

async function toggleFav() {
  if (!song.value) return
  try {
    if (isFav.value) {
      await removeFavorite(song.value.id)
      isFav.value = false
      showSuccess('已取消收藏')
    } else {
      await addFavorite(song.value.id)
      isFav.value = true
      showSuccess('已收藏')
    }
  } catch (error) {
    showError(error, '收藏操作失败')
  }
}

function playSong() {
  if (song.value) player.playSong(song.value)
}

function seekLyric(time: number) {
  if (!song.value) return
  if (player.currentSong?.id !== song.value.id) player.playSong(song.value)
  player.seek(time)
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>
<style scoped>
.detail-page {
  padding: 40px;
  max-width: 800px;
}
.loading {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px;
}
.song-header {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  margin-bottom: 40px;
}
.cover-placeholder {
  width: 160px;
  height: 160px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--accent), var(--accent-deep));
  display: grid;
  place-items: center;
  font-size: 48px;
  color: var(--text-on-accent);
  font-weight: 800;
  flex-shrink: 0;
}
.info h2 {
  color: var(--text);
  font-size: 28px;
  margin: 0 0 8px;
}
.artist {
  color: var(--accent);
  font-size: 16px;
  margin: 0 0 6px;
}
.meta {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 20px;
}
.actions {
  display: flex;
  gap: 12px;
}
.features,
.radar-block,
.detail-block,
.lyrics-section {
  margin-bottom: 32px;
}
.features h3,
.radar-block h3,
.detail-block h3,
.lyrics-section h3 {
  color: var(--text);
  font-size: 18px;
  margin: 0 0 16px;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.feat-item {
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.feat-label {
  color: var(--text-muted);
  font-size: 12px;
}
.feat-val {
  color: var(--text);
  font-size: 20px;
  font-weight: 700;
}
.radar-chart {
  width: 100%;
  height: 320px;
}
.radar-note {
  color: var(--text-muted);
  font-size: 12px;
  margin: 8px 0 0;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag {
  background: var(--accent-soft);
  border: 1px solid var(--border-strong);
  color: var(--accent);
  border-radius: 999px;
  padding: 4px 14px;
  font-size: 13px;
}
.structure-text {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.9;
  background: var(--surface-raised);
  border-radius: 10px;
  padding: 16px 20px;
  margin: 0;
}
.lyrics-text {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 2;
  white-space: pre-wrap;
  background: var(--surface-raised);
  border-radius: 10px;
  padding: 20px;
  margin: 0;
}
.lyrics-list {
  max-height: 360px;
  overflow-y: auto;
  padding: 12px 20px;
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  scrollbar-color: var(--border-strong) transparent;
}
.lyric-line {
  display: block;
  width: 100%;
  padding: 7px 0;
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  line-height: 1.7;
  text-align: left;
  cursor: pointer;
  transition:
    color 0.2s ease,
    transform 0.2s ease;
}
.lyric-line:hover,
.lyric-line.active {
  color: var(--accent);
}
.lyric-line.active {
  font-weight: 700;
  transform: translateX(4px);
}
@media (max-width: 640px) {
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
