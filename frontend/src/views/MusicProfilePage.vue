<!-- 个人画像页面：将历史互动与收藏数据转换为统计卡片和趋势图。 -->
<template>
  <section class="profile-page">
    <PageHeader title="个人内容画像" subtitle="从你的历史互动和收藏记录里，了解内容偏好">
      <template #actions>
        <el-button :loading="loading" @click="loadProfile">刷新数据</el-button>
      </template>
    </PageHeader>

    <StatePanel v-if="loading && profile === null" type="loading" title="正在整理你的音乐画像" />
    <StatePanel
      v-else-if="errorMessage && profile === null"
      type="error"
      title="画像加载失败"
      :message="errorMessage"
    >
      <template #action>
        <button class="retry-button" type="button" @click="loadProfile">重新加载</button>
      </template>
    </StatePanel>

    <template v-else-if="profile">
      <div class="stat-grid">
        <article v-for="stat in stats" :key="stat.label" class="stat-card">
          <span class="stat-icon" aria-hidden="true">{{ stat.icon }}</span>
          <div>
            <p>{{ stat.label }}</p>
            <strong>{{ stat.value }}</strong>
          </div>
        </article>
      </div>

      <div class="profile-grid">
        <article class="panel preference-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">YOUR SOUND</p>
              <h3>常听风格</h3>
            </div>
            <span class="panel-icon">♫</span>
          </div>
          <div v-if="profile.preferred_genres.length" class="genre-tags">
            <span v-for="(genre, index) in profile.preferred_genres" :key="genre" class="genre-tag">
              <small>{{ String(index + 1).padStart(2, '0') }}</small
              >{{ genre }}
            </span>
          </div>
          <div v-else class="panel-empty">产生一些互动后，这里会出现你的内容偏好。</div>
          <div class="feature-list">
            <div v-for="feature in features" :key="feature.label" class="feature-row">
              <div class="feature-label">
                <span>{{ feature.label }}</span
                ><strong>{{ feature.display }}</strong>
              </div>
              <div class="feature-track">
                <span :style="{ width: `${feature.percent}%` }"></span>
              </div>
            </div>
          </div>
        </article>

        <article class="panel trend-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">LAST 30 DAYS</p>
              <h3>互动趋势</h3>
            </div>
            <span class="trend-total">{{ profile.total_plays }} 次互动</span>
          </div>
          <div v-if="profile.play_trend.length" ref="trendChart" class="chart chart-trend"></div>
          <div v-else class="chart-empty">还没有足够的互动记录生成趋势。</div>
        </article>
      </div>

      <div class="chart-grid">
        <article class="panel chart-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">GENRES</p>
              <h3>风格分布</h3>
            </div>
          </div>
          <div
            v-if="profile.genre_distribution.length"
            ref="genreChart"
            class="chart chart-bar"
          ></div>
          <div v-else class="chart-empty">暂无风格数据</div>
        </article>
        <article class="panel chart-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">ARTISTS</p>
              <h3>常听歌手</h3>
            </div>
          </div>
          <div v-if="profile.top_artists.length" ref="artistChart" class="chart chart-bar"></div>
          <div v-else class="chart-empty">暂无歌手数据</div>
        </article>
      </div>

      <article v-if="profile.agent_interpretation" class="panel interpretation-panel">
        <div class="panel-heading">
          <div>
            <p class="panel-kicker">AI INSIGHT</p>
            <h3>智能体解读</h3>
          </div>
          <span class="panel-icon">✦</span>
        </div>
        <p class="interpretation-text">{{ profile.agent_interpretation }}</p>
      </article>

      <div class="insight-grid">
        <article class="panel insight-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">ACTIVE HOURS</p>
              <h3>活跃时段</h3>
            </div>
          </div>
          <div
            v-if="profile.active_hours?.length"
            ref="activeHoursChart"
            class="chart chart-active"
          ></div>
          <div v-else class="chart-empty">暂无互动时间数据</div>
        </article>

        <article class="panel insight-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">INTERESTS</p>
              <h3>兴趣分布</h3>
            </div>
          </div>
          <div
            v-if="profile.interest_distribution?.length"
            ref="interestChart"
            class="chart chart-bar"
          ></div>
          <div v-else class="chart-empty">暂无兴趣分布数据</div>
        </article>
      </div>

      <article v-if="profile.preference_change?.length" class="panel preference-change-panel">
        <div class="panel-heading">
          <div>
            <p class="panel-kicker">PREFERENCE SHIFT</p>
            <h3>偏好变化</h3>
          </div>
        </div>
        <div class="preference-change-list">
          <div
            v-for="item in profile.preference_change"
            :key="item.detail"
            class="preference-change-row"
          >
            <span class="change-period">{{ item.direction }}</span>
            <span class="change-genre">{{ item.detail }}</span>
          </div>
        </div>
      </article>

      <article class="panel recent-panel">
        <div class="panel-heading">
          <div>
            <p class="panel-kicker">RECENTLY PLAYED</p>
            <h3>最近互动</h3>
          </div>
          <router-link to="/songs" class="text-link">去发现更多 →</router-link>
        </div>
        <div v-if="profile.recent_plays.length" class="recent-list">
          <button
            v-for="item in profile.recent_plays"
            :key="`${item.song.id}-${item.played_at}`"
            class="recent-item"
          >
            <span class="song-cover">{{ item.song.title.slice(0, 1) }}</span>
            <span class="song-info">
              <strong>{{ item.song.title }}</strong
              ><small>{{ item.song.artist.name }}</small>
            </span>
            <span class="song-genre">{{ item.song.genre || '未分类' }}</span>
            <time>{{ formatDate(item.played_at) }}</time>
          </button>
        </div>
        <div v-else class="recent-empty">还没有互动记录，先浏览内容数据吧。</div>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { use, init } from 'echarts/core'
import type { ECharts } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import { getMusicProfile } from '../api/profile'
import type { MusicProfileResponse } from '../types/profile'
import { showError } from '../utils/feedback'

use([BarChart, LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const profile = ref<MusicProfileResponse | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const trendChart = ref<HTMLDivElement | null>(null)
const genreChart = ref<HTMLDivElement | null>(null)
const artistChart = ref<HTMLDivElement | null>(null)
const activeHoursChart = ref<HTMLDivElement | null>(null)
const interestChart = ref<HTMLDivElement | null>(null)
const charts = shallowRef<ECharts[]>([])
let resizeObserver: ResizeObserver | null = null

// 将接口统计映射成统一卡片结构，模板无需关心字段来源。
const stats = computed(() => {
  if (!profile.value) return []
  return [
    { label: '累计互动', value: profile.value.total_plays, icon: '◉' },
    { label: '听过歌曲', value: profile.value.unique_songs, icon: '♫' },
    { label: '收藏歌曲', value: profile.value.favorite_count, icon: '♡' },
  ]
})

// 计算特征进度条的展示值和百分比，缺失值保持为空态。
const features = computed(() => {
  const feature = profile.value?.feature_profile
  if (!feature) return []
  return [
    {
      label: '平均 BPM',
      display: formatNumber(feature.average_bpm),
      percent: scale(feature.average_bpm, 200),
    },
    {
      label: '能量 Energy',
      display: formatPercent(feature.average_energy),
      percent: scale(feature.average_energy, 1),
    },
    {
      label: '愉悦 Valence',
      display: formatPercent(feature.average_valence),
      percent: scale(feature.average_valence, 1),
    },
    {
      label: '律动 Danceability',
      display: formatPercent(feature.average_danceability),
      percent: scale(feature.average_danceability, 1),
    },
  ]
})

// 加载画像；图表渲染放在数据更新后，避免读取空 DOM。
async function loadProfile(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await getMusicProfile()
    profile.value = data
    await nextTick()
    renderCharts()
  } catch (error) {
    errorMessage.value = '暂时无法读取播放数据，请稍后重试。'
    showError(error, '音乐画像加载失败')
  } finally {
    loading.value = false
  }
}

// 根据画像数据创建趋势、风格和歌手图表。
function renderCharts(): void {
  disposeCharts()
  const data = profile.value
  if (!data) return

  if (trendChart.value && data.play_trend.length) {
    const chart = init(trendChart.value)
    chart.setOption({
      grid: { left: 8, right: 8, top: 16, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.play_trend.map((item) => item.date.slice(5)),
        axisLabel: { color: '#8f98b0' },
        axisLine: { lineStyle: { color: 'rgba(202,210,255,.14)' } },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: 'rgba(202,210,255,.08)' } },
        axisLabel: { color: '#8f98b0' },
      },
      series: [
        {
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          data: data.play_trend.map((item) => item.count),
          lineStyle: { color: '#8b7cf6', width: 3 },
          itemStyle: { color: '#a99dff' },
          areaStyle: { color: 'rgba(139,124,246,.16)' },
        },
      ],
      tooltip: { trigger: 'axis' },
    })
    charts.value.push(chart)
  }

  createBarChart(genreChart.value, data.genre_distribution)
  createBarChart(artistChart.value, data.top_artists)
  if (data.interest_distribution?.length) {
    createBarChart(
      interestChart.value,
      data.interest_distribution.map((item) => ({
        name: item.label,
        count: Math.round(item.weight * 100),
      })),
    )
  }
  createActiveHoursChart()
  resizeObserver = new ResizeObserver(() => charts.value.forEach((chart) => chart.resize()))
  ;[
    trendChart.value,
    genreChart.value,
    artistChart.value,
    activeHoursChart.value,
    interestChart.value,
  ].forEach((element) => element && resizeObserver?.observe(element))
}

// 创建活跃时段的条形图。
function createActiveHoursChart(): void {
  const element = activeHoursChart.value
  const data = profile.value
  if (!element || !data?.active_hours?.length) return
  const chart = init(element)
  const hours = data.active_hours
  chart.setOption({
    grid: { left: 8, right: 18, top: 16, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: hours.map((item) => `${item.hour}:00`),
      axisLabel: { color: '#8f98b0' },
      axisLine: { lineStyle: { color: 'rgba(202,210,255,.14)' } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: 'rgba(202,210,255,.08)' } },
      axisLabel: { color: '#8f98b0' },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 24,
        data: hours.map((item) => item.weight),
        itemStyle: { color: '#59e2a4', borderRadius: [8, 8, 0, 0] },
      },
    ],
    tooltip: { trigger: 'axis' },
  })
  charts.value.push(chart)
}

// 创建横向柱状图，统一处理颜色、排序和空数据。
function createBarChart(
  element: HTMLDivElement | null,
  items: { name: string; count: number }[],
): void {
  if (!element || !items.length) return
  const chart = init(element)
  chart.setOption({
    grid: { left: 8, right: 18, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(202,210,255,.08)' } },
      axisLabel: { color: '#8f98b0' },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: items.map((item) => item.name),
      axisLabel: { color: '#c3c9dc', width: 92, overflow: 'truncate' },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 16,
        data: items.map((item) => item.count),
        itemStyle: { color: '#59e2a4', borderRadius: [0, 8, 8, 0] },
        label: { show: true, position: 'right', color: '#c3c9dc' },
      },
    ],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  })
  charts.value.push(chart)
}

// 页面卸载或刷新前释放 ECharts 实例，避免重复监听和内存泄漏。
function disposeCharts(): void {
  resizeObserver?.disconnect()
  resizeObserver = null
  charts.value.forEach((chart) => chart.dispose())
  charts.value = []
}

// 将统计值限制在进度条允许的 0~100 区间。
function scale(value: number | null, max: number): number {
  if (value === null) return 0
  return Math.max(0, Math.min(100, (value / max) * 100))
}

// 格式化数值，缺失数据用统一占位符。
function formatNumber(value: number | null): string {
  return value === null ? '—' : value.toFixed(1)
}

// 格式化比例为百分数。
function formatPercent(value: number | null): string {
  return value === null ? '—' : `${Math.round(value * 100)}%`
}

// 将播放时间格式化为中文短日期。
function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '日期未知'
    : date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

onMounted(loadProfile)
onBeforeUnmount(disposeCharts)
</script>

<style scoped>
.profile-page {
  padding: var(--page-gutter);
  max-width: 1380px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}
.stat-card,
.panel {
  border: 1px solid var(--border);
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(39, 56, 85, 0.78), rgba(24, 36, 58, 0.68));
  box-shadow: var(--shadow-soft);
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
}
.stat-icon,
.panel-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  color: var(--accent-strong);
  background: var(--accent-soft);
  font-size: 21px;
}
.stat-card p {
  margin: 0 0 7px;
  color: var(--text-muted);
  font-size: 13px;
}
.stat-card strong {
  color: var(--text);
  font-size: 27px;
  letter-spacing: -0.04em;
}
.profile-grid,
.chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 18px;
  margin-bottom: 18px;
}
.chart-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.panel {
  padding: 22px;
  min-width: 0;
}
.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}
.panel-kicker {
  margin: 0 0 7px;
  color: var(--accent-strong);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
}
.panel h3 {
  margin: 0;
  color: var(--text);
  font-size: 19px;
}
.trend-total {
  color: var(--text-muted);
  font-size: 12px;
}
.genre-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  min-height: 42px;
}
.genre-tag {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 12px;
  border: 1px solid rgba(110, 231, 210, 0.25);
  border-radius: 10px;
  color: var(--text);
  background: var(--accent-soft);
  font-size: 13px;
}
.genre-tag small {
  color: var(--accent-strong);
  font-size: 10px;
}
.feature-list {
  display: grid;
  gap: 15px;
  margin-top: 26px;
}
.feature-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 7px;
  color: var(--text-secondary);
  font-size: 12px;
}
.feature-label strong {
  color: var(--text);
  font-weight: 600;
}
.feature-track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(202, 210, 255, 0.1);
}
.feature-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent), #59e2a4);
}
.chart {
  width: 100%;
  height: 260px;
}
.chart-trend {
  height: 250px;
}
.chart-empty,
.panel-empty,
.recent-empty {
  display: grid;
  place-items: center;
  min-height: 160px;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
}
.recent-panel {
  margin-bottom: 30px;
}
.text-link {
  color: var(--accent-strong);
  font-size: 12px;
  text-decoration: none;
}
.recent-list {
  display: grid;
}
.recent-item {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 120px 72px 24px;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 4px;
  border: 0;
  border-top: 1px solid var(--border);
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.recent-item:hover {
  background: rgba(139, 124, 246, 0.08);
}
.song-cover {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 11px;
  color: var(--text-on-accent);
  background: linear-gradient(135deg, var(--accent-deep), var(--accent));
  font-weight: 700;
}
.song-info {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.song-info strong {
  overflow: hidden;
  color: var(--text);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.song-info small,
.song-genre,
.recent-item time {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.play-mark {
  color: var(--accent-strong);
  font-size: 12px;
}
.retry-button {
  padding: 0;
  border: 0;
  color: var(--accent-strong);
  background: transparent;
  cursor: pointer;
}

/* 智能体解读面板 */
.interpretation-panel {
  margin-bottom: 18px;
}
.interpretation-text {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(110, 231, 210, 0.06), rgba(169, 162, 255, 0.06));
}

/* 洞察面板布局 */
.insight-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
}
.chart-active {
  height: 200px;
}

/* 偏好变化列表 */
.preference-change-panel {
  margin-bottom: 18px;
}
.preference-change-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.preference-change-row {
  display: grid;
  grid-template-columns: 140px 1fr 100px 80px;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}
.change-period {
  color: var(--accent-strong);
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.04em;
}
.change-genre {
  color: var(--text);
  font-weight: 600;
}
.change-score {
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.change-count {
  color: var(--text-muted);
  text-align: right;
}

@keyframes chartActive {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .profile-page {
    padding: 28px 22px;
  }
  .profile-grid,
  .chart-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 620px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
  .recent-item {
    grid-template-columns: 42px minmax(0, 1fr) 24px;
  }
  .song-genre,
  .recent-item time {
    display: none;
  }
  .preference-change-row {
    grid-template-columns: 100px 1fr;
  }
  .change-score,
  .change-count {
    display: none;
  }
}
</style>
