<!-- 首页：先给数据概览，再给推荐列表。装饰元素一律去掉，信息本身承担视觉。 -->
<template>
  <section class="home-page">
    <PageHeader
      :title="auth.user ? '概览' : '内容数据平台'"
      :subtitle="
        auth.user
          ? '你的收听、收藏与反馈会汇总在这里，并参与下一轮推荐。'
          : '按标题、来源和音频特征检索示例内容；登录后可获得个性化推荐。'
      "
    >
      <template #actions>
        <el-button :loading="loading" @click="reload">刷新</el-button>
        <router-link class="button-link" to="/agent">{{
          auth.user ? '打开智能体' : '登录后使用智能体'
        }}</router-link>
      </template>
    </PageHeader>

    <!-- 概览：只在登录且有画像数据时出现，避免给游客看一排 0 -->
    <div v-if="auth.user && profile" class="overview">
      <div v-for="item in overviewStats" :key="item.label" class="overview-item">
        <span>{{ item.label }}</span>
        <strong class="numeric">{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </div>
    </div>

    <div class="home-grid">
      <div class="home-main">
        <div class="section-head">
          <h3>{{ auth.user ? '为你推荐' : '热门内容' }}</h3>
          <div class="section-tools">
            <span v-if="!auth.user" class="section-note">按热度排序，登录后按偏好重排</span>
            <button v-else type="button" class="text-button" :disabled="loading" @click="reload">
              换一批
            </button>
          </div>
        </div>

        <div v-if="loading" class="panel-state page-surface">
          <StatePanel type="loading" title="正在加载推荐" message="结合你的偏好筛选合适的内容" />
        </div>
        <div v-else-if="loadFailed" class="panel-state page-surface">
          <StatePanel
            type="error"
            title="推荐暂时没有加载成功"
            message="检查服务状态后可以重新加载"
          >
            <template #action>
              <el-button size="small" @click="reload">重新加载</el-button>
            </template>
          </StatePanel>
        </div>
        <div v-else-if="cards.length" class="recommendations">
          <RecommendationCard
            v-for="card in cards"
            :key="card.title + card.items.length"
            :card="card"
            :actions="feedbackStore.actions"
            @feedback="handleFeedbackPayload"
            @openAgent="onOpenAgent"
          />
        </div>
        <div v-else-if="hotSongs.length" class="track-list">
          <article v-for="song in hotSongs" :key="song.id" class="track-row">
            <router-link class="track-main" :to="`/songs/${song.id}`">
              <SongCover :song="song" size="md" show-source />
              <span class="track-copy">
                <strong>{{ song.title }}</strong>
                <span class="track-meta">
                  {{ song.artist.name }} · {{ song.genre || '未知风格' }}
                  <template v-if="song.bpm"> · {{ Math.round(song.bpm) }} BPM</template>
                </span>
                <span class="track-reason">{{ song.reason }}</span>
              </span>
            </router-link>
            <span class="track-tail">
              <router-link class="text-button" :to="`/songs/${song.id}`">查看</router-link>
            </span>
          </article>
        </div>
        <div v-else class="panel-state page-surface">
          <StatePanel
            title="还没有足够的推荐数据"
            message="导入示例数据并产生互动记录后，这里会出现个性化推荐"
          >
            <template #action>
              <router-link class="button-link" to="/songs">先去内容数据看看</router-link>
            </template>
          </StatePanel>
        </div>
      </div>

      <aside class="home-side">
        <!-- 特征画像：数据源没提供的项直接不出现，不用 0 占位 -->
        <section v-if="auth.user && featureRows.length" class="side-block">
          <div class="side-head">
            <h3>你的特征</h3>
            <router-link class="text-button" to="/profile">详情</router-link>
          </div>
          <div v-for="row in featureRows" :key="row.label" class="feature-row">
            <div class="feature-label">
              <span>{{ row.label }}</span
              ><strong class="numeric">{{ row.display }}</strong>
            </div>
            <div class="feature-track" aria-hidden="true">
              <span :style="{ width: `${row.percent}%` }"></span>
            </div>
          </div>
          <p v-if="profile?.preferred_genres.length" class="side-note">
            常听风格：{{ profile.preferred_genres.slice(0, 4).join('、') }}
          </p>
        </section>

        <section v-else-if="auth.user" class="side-block">
          <h3>你的特征</h3>
          <p class="side-note">
            产生收听、收藏或反馈后，这里会显示平均节拍、能量和律动。先去
            <router-link class="inline-link" to="/songs">内容库</router-link> 建立几首歌的互动。
          </p>
        </section>

        <section v-if="profile?.recent_plays.length" class="side-block">
          <div class="side-head">
            <h3>最近互动</h3>
            <router-link class="text-button" to="/profile">全部</router-link>
          </div>
          <ul class="recent-list">
            <li
              v-for="item in profile.recent_plays.slice(0, 4)"
              :key="`${item.song.id}-${item.played_at}`"
            >
              <router-link :to="`/songs/${item.song.id}`">
                <span class="recent-title">{{ item.song.title }}</span>
                <span class="recent-meta">
                  {{ item.song.artist.name }} · {{ formatDate(item.played_at) }}
                </span>
              </router-link>
            </li>
          </ul>
        </section>

        <section class="side-block side-block--quiet">
          <h3>数据来源</h3>
          <p class="side-note">
            曲目特征来自 AcousticBrainz 的音频分析，元数据与时长由 MusicBrainz
            补齐。平台不托管音频，也不存储歌词。
          </p>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listRecommendationCards, listRecommendations } from '../api/recommendations'
import { getMusicProfile } from '../api/profile'
import PageHeader from '../components/PageHeader.vue'
import RecommendationCard from '../components/RecommendationCard.vue'
import SongCover from '../components/SongCover.vue'
import StatePanel from '../components/StatePanel.vue'
import type { RecommendationItem, StructuredRecommendationCard } from '../types/music'
import type { MusicProfileResponse } from '../types/profile'
import { useAuthStore } from '../stores/auth'
import { useFeedbackStore } from '../stores/feedback'

const router = useRouter()
const auth = useAuthStore()
const feedbackStore = useFeedbackStore()
const hotSongs = ref<RecommendationItem[]>([])
const cards = ref<StructuredRecommendationCard[]>([])
const profile = ref<MusicProfileResponse | null>(null)
// 初值就是「加载中」：以前初值是 false，而数据在 onMounted 才请求，
// 于是每次进首页都会先渲染一帧「还没有足够的推荐数据」空态再换成推荐卡 —— 一次可见的闪烁。
const loading = ref(true)
const loadFailed = ref(false)

const overviewStats = computed(() => {
  const current = profile.value
  if (!current) return []
  return [
    { label: '互动次数', value: current.total_plays, hint: '记录在案的收听' },
    { label: '收藏', value: current.favorite_count, hint: '当前收藏条目' },
    { label: '反馈', value: feedbackStore.stats?.total ?? 0, hint: '全部反馈记录' },
    { label: '覆盖内容', value: current.unique_songs, hint: '不同的曲目' },
  ]
})

// 特征条形：null 的字段直接不展示，避免出现「0%」造成误读。
const featureRows = computed(() => {
  const feature = profile.value?.feature_profile
  if (!feature) return []
  const rows = [
    {
      label: '平均节拍',
      value: feature.average_bpm,
      max: 180,
      display: feature.average_bpm === null ? '—' : `${Math.round(feature.average_bpm)} BPM`,
    },
    {
      label: '能量',
      value: feature.average_energy,
      max: 1,
      display: formatPercent(feature.average_energy),
    },
    {
      label: '明亮度',
      value: feature.average_valence,
      max: 1,
      display: formatPercent(feature.average_valence),
    },
    {
      label: '律动',
      value: feature.average_danceability,
      max: 1,
      display: formatPercent(feature.average_danceability),
    },
  ]
  return rows
    .filter((row) => row.value !== null)
    .map((row) => ({
      label: row.label,
      display: row.display,
      percent: Math.min(100, Math.max(0, ((row.value ?? 0) / row.max) * 100)),
    }))
})

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${Math.round(value * 100)}%`
}

// 把互动时间压成「月 日」，侧栏只需要一个时间锚点。
function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '日期未知'
    : date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

async function loadRecommendations(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    if (auth.user) {
      const { data } = await listRecommendationCards()
      cards.value = data
    } else {
      const { data } = await listRecommendations()
      hotSongs.value = data.items
    }
  } catch {
    hotSongs.value = []
    cards.value = []
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

// 画像只对登录用户请求；失败时静默降级，不影响推荐区。
async function loadProfile(): Promise<void> {
  if (!auth.user) {
    profile.value = null
    return
  }
  try {
    const { data } = await getMusicProfile()
    profile.value = data
  } catch {
    profile.value = null
  }
}

async function reload(): Promise<void> {
  await Promise.all([loadRecommendations(), loadProfile()])
}

// 在应用内切换到智能体页并带入话题，避免反复打开新标签页。
function onOpenAgent(payload: { type: string; query: string }) {
  void router.push({ name: 'agent', query: { topic: payload.query } })
}

// 反馈提交后对“不喜欢”的歌曲立刻从推荐中移除，形成反馈闭环；其余动作只记录统计。
async function handleFeedbackPayload(payload: { songId: number; action: string }): Promise<void> {
  if (payload.action === 'dislike') await loadRecommendations()
}

onMounted(async () => {
  // 首页是公开路由，守卫不会等认证恢复；这里必须显式等一次。
  // 否则会先按游客加载热门内容，登录态回来后又把标题换成「为你推荐」，
  // 页面就停在「推荐标题 + 游客数据」的错位状态。
  await auth.initialize()
  await Promise.all([
    feedbackStore.loadActions(),
    feedbackStore.loadStats(),
    loadRecommendations(),
    loadProfile(),
  ])
})
</script>

<style scoped>
.home-page {
  padding: var(--page-gutter);
}

.button-link {
  display: inline-flex;
  height: 32px;
  align-items: center;
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  color: var(--text);
  background: transparent;
  font-size: var(--fs-xs);
  text-decoration: none;
}

.button-link:hover {
  background: var(--surface-hover);
}

/* 概览条：四项并排，用分隔线而不是卡片分隔 */
.overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 28px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.overview-item {
  padding: 14px 16px;
  border-left: 1px solid var(--border);
}

.overview-item:first-child {
  border-left: 0;
}

.overview-item span,
.overview-item small {
  display: block;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.overview-item strong {
  display: block;
  margin: 4px 0 2px;
  color: var(--text);
  font-size: var(--fs-xl);
  font-weight: 600;
  line-height: 1.2;
}

.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 288px;
  gap: 32px;
  align-items: start;
}

.home-main {
  min-width: 0;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.section-head h3 {
  margin: 0;
  color: var(--text);
  font-size: var(--fs-lg);
  font-weight: 600;
}

.section-tools {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-note {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.text-button {
  padding: 0;
  border: 0;
  color: var(--text-muted);
  background: transparent;
  font-family: inherit;
  font-size: var(--fs-xs);
  text-decoration: none;
  cursor: pointer;
}

.text-button:hover {
  color: var(--text);
}

.text-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-state {
  display: flex;
  min-height: var(--content-min-height);
  align-items: center;
  justify-content: center;
}

/* 热门列表：行之间只用分隔线，不套卡片 */
.track-list {
  border-top: 1px solid var(--border);
}

.track-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.track-main {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.track-copy {
  min-width: 0;
}

.track-copy strong,
.track-meta,
.track-reason {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-copy strong {
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 500;
}

.track-meta {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.track-reason {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}

.track-tail {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 12px;
}

.home-side {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.side-block h3 {
  margin: 0 0 10px;
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.side-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.side-head h3 {
  margin: 0;
}

.side-block--quiet h3 {
  color: var(--text-secondary);
}

.side-note {
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.7;
}

.inline-link {
  color: var(--text-secondary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.feature-row + .feature-row {
  margin-top: 10px;
}

.feature-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
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
  border-radius: 2px;
  background: var(--surface-hover);
}

.feature-track span {
  display: block;
  height: 100%;
  border-radius: 2px;
  background: var(--accent);
}

.recent-list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.recent-list a {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 7px 0;
  border-top: 1px solid var(--border);
  text-decoration: none;
}

.recent-list li:first-child a {
  border-top: 0;
  padding-top: 0;
}

.recent-list a:hover .recent-title {
  color: var(--text);
}

.recent-title,
.recent-meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-title {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}

.recent-meta {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

@media (max-width: 1100px) {
  .home-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 28px;
  }
}

@media (max-width: 720px) {
  .overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-item {
    border-top: 1px solid var(--border);
  }

  .overview-item:nth-child(odd) {
    border-left: 0;
  }

  .text-button {
    display: inline-flex;
    min-height: 32px;
    align-items: center;
  }

  .track-tail {
    display: none;
  }
}
</style>
