<!-- 个人画像页面：将历史互动与收藏数据转换为统计卡片和趋势图。 -->
<template>
  <section class="profile-page">
    <PageHeader title="个人分析" subtitle="从你的历史互动和收藏记录里，了解内容偏好">
      <template #actions>
        <el-button :loading="loading" @click="() => loadProfile(true)">刷新数据</el-button>
      </template>
    </PageHeader>

    <StatePanel v-if="loading && profile === null" type="loading" title="正在整理你的内容画像" />
    <StatePanel
      v-else-if="errorMessage && profile === null"
      type="error"
      title="画像加载失败"
      :message="errorMessage"
    >
      <template #action>
        <button class="retry-button" type="button" @click="() => loadProfile(true)">
          重新加载
        </button>
      </template>
    </StatePanel>

    <template v-else-if="profile">
      <!-- 还没有任何互动记录时，页面照常展示框架，只说明数据从哪来 -->
      <p v-if="refreshing" class="refresh-note">正在后台刷新…</p>
      <div
        v-if="profile.total_plays === 0 && profile.favorite_count === 0 && feedbackCount === 0"
        class="empty-hint"
      >
        <strong class="empty-hint-title">还没有可分析的互动数据</strong>
        <p>
          画像来自你的<strong>收藏</strong>、<strong>收听记录</strong>与<strong>反馈</strong>。去
          <router-link to="/songs">内容库</router-link> 收藏几首、在歌曲详情点「记一次收听」，或让
          <router-link to="/agent">智能体</router-link> 推荐一批，数据就会出现在这里。
        </p>
      </div>
      <div class="stat-grid">
        <article v-for="stat in stats" :key="stat.label" class="stat-card">
          <div>
            <p>{{ stat.label }}</p>
            <strong class="numeric">{{ stat.value }}</strong>
          </div>
        </article>
      </div>

      <div class="profile-grid">
        <article class="panel preference-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">你的偏好</p>
              <h3>常听风格</h3>
            </div>
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
            <p v-if="hiddenFeatureCount" class="feature-note">
              有 {{ hiddenFeatureCount }} 项特征因分析源未提供而隐藏（不用 0
              冒充）；律动是「可舞动」分类器的判定分，按互动记录取平均，适合看档位而不是精确百分比。
            </p>
          </div>
        </article>

        <article class="panel trend-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">近 30 天</p>
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
              <p class="panel-kicker">你听的内容</p>
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
              <p class="panel-kicker">Top 5</p>
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
            <p class="panel-kicker">根据你的记录</p>
            <h3>解读</h3>
          </div>
        </div>
        <p class="interpretation-text">{{ profile.agent_interpretation }}</p>
      </article>

      <div class="insight-grid">
        <article class="panel insight-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">按小时统计</p>
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
              <p class="panel-kicker">按标签统计</p>
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
            <p class="panel-kicker">近两期对比</p>
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
            <p class="panel-kicker">最近播放</p>
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
            <SongCover :song="item.song" size="sm" />
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
import SongCover from '../components/SongCover.vue'
import { useProfileStore } from '../stores/profile'
import { useFeedbackStore } from '../stores/feedback'
import { storeToRefs } from 'pinia'
import { danceabilityAverageLabel } from '../types/music'

use([BarChart, LineChart, GridComponent, TooltipComponent, CanvasRenderer])

// 画像放进 store 缓存：再次进入页面立刻用缓存渲染，不再每次都等接口。
const profileStore = useProfileStore()
const feedbackStore = useFeedbackStore()
// 反馈数单独取：它是画像里唯一完全由用户主动产生的信号
const feedbackCount = computed(() => feedbackStore.stats?.total ?? 0)
const { profile, loading, refreshing, errorMessage } = storeToRefs(profileStore)
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
    { label: '累计互动', value: profile.value.total_plays },
    { label: '浏览条目', value: profile.value.unique_songs },
    { label: '收藏条目', value: profile.value.favorite_count },
    { label: '主动反馈', value: feedbackCount.value },
  ]
})

// 特征行：百分比为 0 表示数据源没给这个字段，展示时整行去掉，避免出现永远空着的进度条。
const featureRows = computed(() => {
  const feature = profile.value?.feature_profile
  if (!feature) return []
  const dancePercent = formatPercent(feature.average_danceability)
  const danceLevel = danceabilityAverageLabel(feature.average_danceability)
  return [
    {
      label: '平均 BPM',
      display: formatNumber(feature.average_bpm),
      percent: scale(feature.average_bpm, 200),
    },
    {
      label: '能量',
      display: formatPercent(feature.average_energy),
      percent: scale(feature.average_energy, 1),
    },
    {
      label: '明亮度',
      display: formatPercent(feature.average_valence),
      percent: scale(feature.average_valence, 1),
    },
    {
      label: '律动',
      display: danceLevel ? `${dancePercent}（${danceLevel}）` : dancePercent,
      percent: scale(feature.average_danceability, 1),
    },
  ]
})

const features = computed(() => featureRows.value.filter((item) => item.percent > 0))
const hiddenFeatureCount = computed(
  () => featureRows.value.filter((item) => item.percent <= 0).length,
)

// 加载画像：数据来自 store 缓存，命中缓存时立即渲染、后台静默刷新。
async function loadProfile(force = true): Promise<void> {
  await profileStore.fetchProfile(force)
  await nextTick()
  renderCharts()
}

// 根据画像数据创建趋势、风格和歌手图表。
function renderCharts(): void {
  disposeCharts()
  const data = profile.value
  if (!data) return
  // 图表颜色统一从设计令牌读取，避免页面换色后图表还是旧配色。
  const muted = cssVariable('--text-muted')
  const secondary = cssVariable('--text-secondary')
  const accent = cssVariable('--accent')
  const border = cssVariable('--chart-border')
  const borderStrong = cssVariable('--chart-border-strong')
  const accentSoft = cssVariable('--chart-accent-fill')

  if (trendChart.value && data.play_trend.length) {
    const chart = init(trendChart.value)
    chart.setOption({
      grid: { left: 8, right: 8, top: 16, bottom: 8, containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.play_trend.map((item) => item.date.slice(5)),
        axisLabel: { color: muted },
        axisLine: { lineStyle: { color: borderStrong } },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: border } },
        axisLabel: { color: muted },
      },
      series: [
        {
          type: 'line',
          smooth: false,
          symbol: 'circle',
          symbolSize: 4,
          data: data.play_trend.map((item) => item.count),
          lineStyle: { color: accent, width: 1.5 },
          itemStyle: { color: accent },
          areaStyle: { color: accentSoft },
        },
      ],
      tooltip: { trigger: 'axis' },
    })
    charts.value.push(chart)
  }

  createBarChart(genreChart.value, data.genre_distribution, { muted, secondary, border, accent })
  createBarChart(artistChart.value, data.top_artists, { muted, secondary, border, accent })
  if (data.interest_distribution?.length) {
    createBarChart(
      interestChart.value,
      data.interest_distribution.map((item) => ({
        name: item.label,
        count: Math.round(item.weight * 100),
      })),
      { muted, secondary, border, accent },
    )
  }
  createActiveHoursChart({ muted, border, accent })
  resizeObserver = new ResizeObserver(() => charts.value.forEach((chart) => chart.resize()))
  ;[
    trendChart.value,
    genreChart.value,
    artistChart.value,
    activeHoursChart.value,
    interestChart.value,
  ].forEach((element) => element && resizeObserver?.observe(element))
}

// 从全局设计令牌读取图表颜色，保证 ECharts 与页面主题同步。
function cssVariable(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

// 创建活跃时段的条形图。
function createActiveHoursChart(palette: { muted: string; border: string; accent: string }): void {
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
      axisLabel: { color: palette.muted },
      axisLine: { lineStyle: { color: palette.border } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: palette.border } },
      axisLabel: { color: palette.muted },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 20,
        data: hours.map((item) => item.weight),
        itemStyle: { color: palette.accent },
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
  palette: { muted: string; secondary: string; border: string; accent: string },
): void {
  if (!element || !items.length) return
  const chart = init(element)
  chart.setOption({
    grid: { left: 8, right: 18, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: palette.border } },
      axisLabel: { color: palette.muted },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: items.map((item) => item.name),
      axisLabel: { color: palette.secondary, width: 92, overflow: 'truncate' },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 14,
        data: items.map((item) => item.count),
        itemStyle: { color: palette.accent },
        label: { show: true, position: 'right', color: palette.secondary },
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

onMounted(async () => {
  void feedbackStore.loadStats()
  if (profile.value !== null) {
    // 命中缓存：先把图表画出来，用户不用等接口
    await nextTick()
    renderCharts()
    void profileStore.fetchProfile(true)
    return
  }
  await loadProfile(false)
})
onBeforeUnmount(disposeCharts)
</script>

<style scoped>
.profile-page {
  padding: var(--page-gutter);
  max-width: 1380px;
}
/* 空数据说明：页面框架照常渲染，只把“数据从哪来”讲清楚 */
.refresh-note {
  margin: 0 0 10px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.empty-hint {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
/* 只让标题块级显示：这条规则以前会命中段落里的 <strong>，
   把整句拆成一行一个词，并把顿号、句号甩到行首。 */
.empty-hint .empty-hint-title {
  display: block;
  margin-bottom: 6px;
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 600;
}
.empty-hint p strong {
  color: var(--text-secondary);
  font-weight: 600;
}
.empty-hint p {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.7;
}
.empty-hint a {
  color: var(--text-secondary);
  text-decoration: underline;
  text-underline-offset: 2px;
}
/* 四个统计值排成一条，靠分隔线区分，不摆四张卡 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 20px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
.stat-card {
  padding: 14px 16px;
  border-left: 1px solid var(--border);
}
.stat-card:first-child {
  border-left: 0;
}
.stat-card p {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.stat-card strong {
  color: var(--text);
  font-size: var(--fs-xl);
  font-weight: 600;
  line-height: 1.2;
}
.profile-grid,
.chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.chart-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.panel {
  min-width: 0;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.panel-kicker {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.panel h3 {
  margin: 0;
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 600;
}
.trend-total {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.genre-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
}
.genre-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
  font-size: var(--fs-xs);
}
.genre-tag small {
  color: var(--text-muted);
  font-size: 11px;
}
.feature-list {
  display: grid;
  gap: 12px;
  margin-top: 22px;
}
.feature-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.feature-label strong {
  color: var(--text-secondary);
  font-weight: 500;
}
.feature-track {
  height: 3px;
  overflow: hidden;
  border-radius: 2px;
  background: var(--surface-hover);
}
.feature-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--accent);
}
.feature-note {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.7;
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
  font-size: var(--fs-xs);
  text-align: center;
}
.recent-panel {
  margin-bottom: 24px;
}
.text-link {
  color: var(--text-muted);
  font-size: var(--fs-xs);
  text-decoration: none;
}
.text-link:hover {
  color: var(--text);
}
.recent-list {
  display: grid;
}
.recent-item {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 120px 64px;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 2px;
  border: 0;
  border-top: 1px solid var(--border);
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.recent-item:hover {
  background: var(--surface-hover);
}
.song-info {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.song-info strong {
  overflow: hidden;
  color: var(--text);
  font-size: var(--fs-xs);
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.song-info small,
.song-genre,
.recent-item time {
  overflow: hidden;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.retry-button {
  padding: 0;
  border: 0;
  color: var(--text-secondary);
  background: transparent;
  font-size: var(--fs-xs);
  text-decoration: underline;
  cursor: pointer;
}

/* 智能体解读面板 */
.interpretation-panel {
  margin-bottom: 16px;
}
.interpretation-text {
  margin: 0;
  padding: 0 0 0 12px;
  border-left: 2px solid var(--border-strong);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.8;
}

/* 洞察面板布局 */
.insight-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.chart-active {
  height: 200px;
}

/* 偏好变化列表 */
.preference-change-panel {
  margin-bottom: 16px;
}
.preference-change-list {
  display: flex;
  flex-direction: column;
}
.preference-change-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  align-items: center;
  gap: 12px;
  padding: 9px 0;
  border-top: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.change-period {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.change-genre {
  color: var(--text);
}

@media (max-width: 900px) {
  .profile-page {
    padding: var(--page-gutter);
  }
  .profile-grid,
  .chart-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 980px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .stat-card:nth-child(3) {
    border-left: 0;
  }
  .stat-card:nth-child(n + 3) {
    border-top: 1px solid var(--border);
  }
}
@media (max-width: 620px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .stat-card,
  .stat-card:nth-child(3) {
    border-left: 1px solid var(--border);
  }
  .stat-card:nth-child(odd) {
    border-left: 0;
  }
  .stat-card:nth-child(n + 3) {
    border-top: 1px solid var(--border);
  }
  .recent-item {
    grid-template-columns: 40px minmax(0, 1fr);
  }
  .song-genre,
  .recent-item time {
    display: none;
  }
  .preference-change-row {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
