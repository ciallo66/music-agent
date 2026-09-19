<!-- 内容详情页：展示结构化特征、雷达图、数据来源说明和收藏/收听记录操作。 -->
<template>
  <section v-if="song" class="detail-page">
    <div class="song-header">
      <div class="cover-placeholder">{{ song.title.slice(0, 1) }}</div>
      <div class="info">
        <h2>{{ song.title }}</h2>
        <p class="artist">{{ song.artist.name }}</p>
        <p class="meta">
          {{ song.genre || '流派待判定' }} · {{ song.language || '—' }} ·
          {{ song.bpm ? Math.round(song.bpm) + ' BPM' : '节拍未知' }}
        </p>
        <p v-if="genreFusion" class="meta meta-sub">
          模型判定：{{ genreFusion }}（不是官方流派标签）
        </p>
        <div class="actions">
          <el-button @click="toggleFav">{{ isFav ? '已收藏' : '收藏' }}</el-button>
          <el-button
            :loading="recording"
            :disabled="!canRecordPlay || played"
            :title="recordPlayHint"
            @click="recordPlayOnce"
          >
            {{ played ? '已记录收听' : '记一次收听' }}
          </el-button>
        </div>
        <p class="actions-note">
          本平台不托管音频，「记一次收听」=
          把你这次的收听行为记进画像（影响互动趋势、活跃时段与风格偏好）。未登录时先登录。
        </p>
      </div>
    </div>
    <div class="features">
      <h3>音乐特征</h3>
      <div class="feature-grid">
        <div class="feat-item">
          <span class="feat-label">节拍</span
          ><span class="feat-val">{{ song.bpm ? Math.round(song.bpm) + ' BPM' : '-' }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">调性</span
          ><span class="feat-val">{{ song.music_key || '-' }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">律动（分档）</span
          ><span class="feat-val" :title="danceabilityHint(song.danceability)">{{
            danceabilityLabel(song.danceability) || '-'
          }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">律动（判定分）</span
          ><span class="feat-val">{{ danceabilityPercent(song.danceability) }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">响度</span
          ><span class="feat-val">{{
            song.loudness !== null ? song.loudness.toFixed(2) : '-'
          }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">人声/器乐</span
          ><span class="feat-val">{{ voiceLabel(song.voice_instrumental) || '-' }}</span>
        </div>
        <div class="feat-item">
          <span class="feat-label">人声概率</span
          ><span class="feat-val">{{
            song.voice_probability !== null ? (song.voice_probability * 100).toFixed(0) + '%' : '-'
          }}</span>
        </div>
      </div>
      <div v-if="moodTags(song.mood_labels).length" class="tag-list mood-list">
        <span v-for="tag in moodTags(song.mood_labels)" :key="tag" class="tag">{{ tag }}</span>
      </div>
    </div>

    <!-- 频谱与节奏：这些是音频分析里真实存在、信息量最大的一批特征 -->
    <div class="detail-block">
      <h3>音频特征明细</h3>
      <div class="feature-grid">
        <div v-for="item in audioFeatures" :key="item.label" class="feat-item">
          <span class="feat-label">{{ item.label }}</span
          ><span class="feat-val">{{ item.value }}</span>
        </div>
      </div>
      <p class="feature-source">
        来源：AcousticBrainz 音频分析（Essentia）。响度是数据源的 average_loudness，已归一化到
        0–1；律动是「可舞动」分类器的判定概率，因此单曲更适合作分档参考，精确分值仅备查。
      </p>
    </div>
    <div class="radar-block">
      <h3>特征画像</h3>
      <div ref="chartEl" class="radar-chart"></div>
      <p class="radar-note">
        五个轴都是数据源真实存在的字段，数值已归一化到 0–100（起音密度 0–8 次/秒、频谱质心 0–4000
        Hz、响度 0–1、律动 0–1、节拍 0–180）；原生 energy 与 valence 数据源未提供，
        不画进图里，也不以 0 冒充。
      </p>
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
    <div class="detail-block missing-block" v-if="missingFields.length">
      <h3>数据来源与缺失字段</h3>
      <p class="structure-text">
        结构化特征来自 AcousticBrainz 音频分析（Essentia）；当前数据源未提供：{{
          missingFields.join('、')
        }}。这些字段不参与展示，也不会用 0 或占位值代替。歌词在本平台不做存储与展示（版权），
        文本类字段不进入数据库。
      </p>
    </div>
  </section>
  <section v-else class="detail-page">
    <div class="detail-state page-surface">
      <StatePanel v-if="loading" type="loading" title="正在加载歌曲详情" />
      <StatePanel
        v-else
        type="error"
        title="歌曲详情加载失败"
        message="歌曲可能不存在，或服务暂时不可用"
      >
        <template #action><el-button type="primary" @click="load">重新加载</el-button></template>
      </StatePanel>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { use, init } from 'echarts/core'
import type { ECharts } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getSong, type SongDetail } from '../api/songs'
import { recordPlay } from '../api/recommendations'
import { useAuthStore } from '../stores/auth'
import {
  danceabilityHint,
  danceabilityLabel,
  danceabilityPercent,
  moodTags,
  voiceLabel,
} from '../types/music'
import { fusedGenreLabel } from '../utils/genre'
import { addFavorite, listFavorites, removeFavorite } from '../api/favorites'
import { showError, showSuccess } from '../utils/feedback'
import StatePanel from '../components/StatePanel.vue'

use([RadarChart, TooltipComponent, LegendComponent, CanvasRenderer])

const route = useRoute()
const auth = useAuthStore()
const song = ref<SongDetail | null>(null)
const loading = ref(false)
const isFav = ref(false)
const recording = ref(false)
const played = ref(false)

// 登录用户都能记录收听（演示账号也属于正常使用）；未登录时引导先登录。
const canRecordPlay = computed(() => auth.isAuthenticated)
const recordPlayHint = computed(() =>
  auth.isAuthenticated ? '记录一次收听，用于你的个人分析' : '登录后可以记录收听',
)

// 多体系投票得出的流派说明（比单一体系更可解释）
const genreFusion = computed(() => fusedGenreLabel(song.value?.genre_labels ?? null))

const chartEl = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null

const instruments = computed(() =>
  (song.value?.instruments ?? '')
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean),
)

// 音频特征明细：优先展示数据源真实存在、且信息量大的字段。
// energy 不在源数据里，这里用响度派生并在界面上标注，避免假装它是原生指标。
const audioFeatures = computed(() => {
  const current = song.value
  if (!current) return []
  const spectral = current.spectral_features
  const rhythm = current.rhythm_features
  const tonal = current.tonal_features

  const num = (value: unknown): number | null =>
    typeof value === 'number' && Number.isFinite(value) ? value : null
  const fixed = (value: unknown, digits = 3): string => {
    const parsed = num(value)
    return parsed === null ? '-' : parsed.toFixed(digits)
  }

  const loudness = num(current.loudness)
  const spectralDynamic =
    spectral && typeof spectral.dynamic_complexity === 'number' ? spectral.dynamic_complexity : null
  const mean = (key: string): unknown => {
    const bag = spectral?.[key]
    return bag && typeof bag === 'object' ? (bag as Record<string, unknown>).mean : undefined
  }

  const rows: { label: string; value: string }[] = [
    { label: '能量（由响度派生）', value: loudness === null ? '-' : loudness.toFixed(2) },
    { label: '起始速率', value: fixed(rhythm?.onset_rate) },
    { label: '拍数', value: fixed(rhythm?.beats_count, 0) },
    { label: '调性强度', value: fixed(tonal?.key_strength) },
    { label: '调式', value: tonal?.key_scale ? String(tonal.key_scale) : '-' },
    { label: '和弦调性', value: tonal?.chords_key ? String(tonal.chords_key) : '-' },
    { label: '频谱质心', value: fixed(mean('spectral_centroid'), 1) },
    { label: '频谱滚降', value: fixed(mean('spectral_rolloff'), 1) },
    { label: '频谱通量', value: fixed(mean('spectral_flux'), 4) },
    { label: '频谱熵', value: fixed(mean('spectral_entropy'), 3) },
    { label: '不协和度', value: fixed(mean('dissonance'), 3) },
    { label: '动态复杂度', value: fixed(spectralDynamic, 3) },
  ]
  return rows.filter((row) => row.value !== '-')
})

// 数据源没提供的字段如实列出，避免页面上出现一排没有意义的「-」。
const missingFields = computed(() => {
  const current = song.value
  if (!current) return []
  const checks: { label: string; value: unknown }[] = [
    { label: '原生 energy / valence（数据源未提供，不入特征图）', value: current.energy },
    { label: '时长', value: current.duration },
    { label: '乐器', value: current.instruments },
    { label: '歌曲结构', value: current.song_structure },
  ]
  return checks.filter((item) => item.value === null || item.value === '').map((item) => item.label)
})

// 加载详情后绘制特征图，再单独查询收藏状态；后者失败不阻断详情展示。
async function load(): Promise<void> {
  loading.value = true
  try {
    const { data } = await getSong(Number(route.params.id))
    song.value = data
  } catch (error) {
    showError(error, '歌曲详情加载失败')
    return
  } finally {
    loading.value = false
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

// 取频谱特征里的均值，供特征明细与雷达图共用；缺失返回 null。
function spectralMean(features: Record<string, unknown> | null | undefined, key: string) {
  const bag = features?.[key]
  if (!bag || typeof bag !== 'object') return null
  const mean = (bag as Record<string, unknown>).mean
  return typeof mean === 'number' && Number.isFinite(mean) ? mean : null
}

// 将 value 从 0~max 线性映射到 0~100 并夹紧边界；缺失返回 0 但不参与展示判定。
function scaleTo100(value: number | null, max: number) {
  if (value === null || !Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, (value / max) * 100))
}

// 从全局设计令牌读取图表颜色，保证 ECharts 与页面主题同步。
function cssVariable(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

// 将歌曲特征转换为雷达图配置。
// 五个轴全部来自数据源真实字段：原生 energy / valence 整列为空，
// 画进来只会是一条贴边的零线，因此不设这两个轴（缺失字段在页面下方如实列出）。
function renderRadar() {
  if (!song.value || !chartEl.value) return
  if (!chart) chart = init(chartEl.value)
  const current = song.value
  const onsetRate =
    typeof current.rhythm_features?.onset_rate === 'number'
      ? current.rhythm_features.onset_rate
      : null
  const centroid = spectralMean(current.spectral_features, 'spectral_centroid')
  const values = [
    scaleTo100(onsetRate, 8),
    scaleTo100(centroid, 4000),
    scaleTo100(current.loudness, 1),
    scaleTo100(current.danceability, 1),
    scaleTo100(current.bpm, 180),
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
        { name: '起音密度', max: 100 },
        { name: '频谱质心', max: 100 },
        { name: '响度', max: 100 },
        { name: '律动', max: 100 },
        { name: '节拍', max: 100 },
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

// 页面尺寸变化时重算图表，避免容器变化导致绘制溢出。
function onResize() {
  chart?.resize()
}

// 按当前状态调用收藏/取消收藏接口，并在成功后更新按钮状态。
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

// 记录一次收听：成功后禁用按钮，避免同一次浏览被反复计入互动趋势。
async function recordPlayOnce() {
  if (!song.value || recording.value || played.value) return
  recording.value = true
  try {
    await recordPlay(song.value.id)
    played.value = true
    showSuccess('已记录一次收听')
  } catch (error) {
    showError(error, '记录收听失败')
  } finally {
    recording.value = false
  }
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
  max-width: 1040px;
  padding: var(--page-gutter);
}
.detail-state {
  min-height: 420px;
}
.song-header {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  margin-bottom: 24px;
  padding: clamp(22px, 4vw, 36px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background:
    radial-gradient(circle at 92% 15%, rgba(110, 231, 210, 0.18), transparent 28%),
    linear-gradient(145deg, rgba(40, 58, 89, 0.82), rgba(24, 37, 61, 0.74));
  box-shadow: var(--shadow-soft);
}
.cover-placeholder {
  width: 160px;
  height: 160px;
  border-radius: 20px;
  background: linear-gradient(145deg, var(--accent), var(--accent-blue));
  box-shadow: 0 22px 50px rgba(22, 186, 165, 0.2);
  display: grid;
  place-items: center;
  font-size: 48px;
  color: var(--text-on-accent);
  font-weight: 800;
  flex-shrink: 0;
}
.info h2 {
  color: var(--text);
  font-size: clamp(28px, 4vw, 42px);
  letter-spacing: -0.04em;
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
.detail-block {
  margin-bottom: 18px;
  padding: clamp(18px, 3vw, 26px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: linear-gradient(145deg, rgba(37, 53, 81, 0.72), rgba(24, 35, 56, 0.62));
  box-shadow: var(--shadow-soft);
}
.meta-sub {
  color: var(--text-muted);
  font-size: 11px;
}
.features h3,
.radar-block h3,
.detail-block h3 {
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
.feature-source {
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.7;
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
.actions-note {
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.7;
}
@media (max-width: 640px) {
  .song-header {
    align-items: center;
    flex-direction: column;
    text-align: center;
  }
  .actions {
    justify-content: center;
  }
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
