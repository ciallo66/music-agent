<!-- 首页聚合入口：提供快捷操作和个性化推荐。 -->
<template>
  <section class="home-page">
    <div class="hero page-surface">
      <div class="hero-copy">
        <p class="eyebrow">GOOD TO SEE YOU</p>
        <h1>欢迎回来，{{ auth.user?.username }}</h1>
        <p>从音乐库开始探索，或让 AI 根据你的播放与收藏记录给出更懂你的建议。</p>
        <div class="hero-actions">
          <router-link class="primary-link" to="/songs">探索音乐库 <span>→</span></router-link>
          <router-link class="secondary-link" to="/agent">问问 AI 助手</router-link>
        </div>
      </div>
      <div class="hero-orbit" aria-hidden="true">
        <div class="record"><span>♫</span></div>
        <i class="orbit-dot dot-one"></i><i class="orbit-dot dot-two"></i>
      </div>
    </div>

    <div class="section-heading">
      <div>
        <p>QUICK ACCESS</p>
        <h2>快速开始</h2>
      </div>
      <span>把常用功能放在触手可及的位置</span>
    </div>
    <div class="quick-actions">
      <router-link v-for="item in quickActions" :key="item.to" :to="item.to" class="action-card">
        <span class="action-icon" :class="item.tone" aria-hidden="true">{{ item.icon }}</span>
        <span class="action-copy"
          ><strong>{{ item.label }}</strong
          ><small>{{ item.description }}</small></span
        >
        <span class="arrow" aria-hidden="true">→</span>
      </router-link>
    </div>

    <div class="section-heading recommendation-heading">
      <div>
        <p>MADE FOR YOU</p>
        <h2>为你推荐</h2>
      </div>
      <router-link to="/profile">查看音乐画像 →</router-link>
    </div>
    <div v-if="loading" class="recommendation-state page-surface">
      <StatePanel type="loading" title="正在生成推荐" message="结合你的偏好寻找合适的音乐" />
    </div>
    <div v-else-if="hotSongs.length" class="hot-grid">
      <article
        v-for="(song, index) in hotSongs"
        :key="song.id"
        class="hot-card page-surface"
        @click="goDetail(song.id)"
      >
        <div class="hot-cover" :class="`tone-${index % 4}`">
          <span>{{ song.title.slice(0, 1) }}</span
          ><small>{{ String(index + 1).padStart(2, '0') }}</small>
        </div>
        <div class="hot-info">
          <strong>{{ song.title }}</strong>
          <span>{{ song.artist.name }}</span>
          <small>{{ song.reason }}</small>
          <p>
            {{ song.genre || '未知风格'
            }}<template v-if="song.bpm"> · {{ Math.round(song.bpm) }} BPM</template>
          </p>
        </div>
        <button type="button" :aria-label="`播放 ${song.title}`" @click.stop="play(song)">▶</button>
      </article>
    </div>
    <div v-else class="recommendation-state page-surface">
      <StatePanel
        :type="loadFailed ? 'error' : 'empty'"
        :title="loadFailed ? '推荐暂时没有加载成功' : '还没有足够的推荐数据'"
        :message="
          loadFailed
            ? '检查服务状态后可以重新加载'
            : '导入歌曲并产生播放记录后，这里会出现个性化推荐'
        "
      >
        <template #action>
          <el-button v-if="loadFailed" type="primary" @click="loadRecommendations"
            >重新加载</el-button
          >
          <router-link v-else class="state-link" to="/songs">先去音乐库看看</router-link>
        </template>
      </StatePanel>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listRecommendations } from '../api/recommendations'
import StatePanel from '../components/StatePanel.vue'
import type { RecommendationItem } from '../types/music'
import { useAuthStore } from '../stores/auth'
import { usePlayerStore } from '../stores/player'

const quickActions = [
  { to: '/songs', label: '音乐库', description: '浏览全部歌曲与音频特征', icon: '♫', tone: 'mint' },
  {
    to: '/playlists',
    label: '我的歌单',
    description: '整理属于你的播放列表',
    icon: '▤',
    tone: 'purple',
  },
  { to: '/favorites', label: '收藏', description: '重温你标记过的声音', icon: '♡', tone: 'rose' },
  { to: '/search', label: '搜索', description: '快速定位歌曲与歌手', icon: '⌕', tone: 'blue' },
]
const auth = useAuthStore()
const router = useRouter()
const player = usePlayerStore()
const hotSongs = ref<RecommendationItem[]>([])
const loading = ref(false)
const loadFailed = ref(false)

// 拉取推荐；失败时转为空状态，避免首页被异常打断。
async function loadRecommendations(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    const { data } = await listRecommendations()
    hotSongs.value = data.items
  } catch {
    hotSongs.value = []
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

// 播放推荐歌曲，并将当前推荐结果设为播放队列。
function play(song: RecommendationItem): void {
  player.playSong(song)
  player.setQueue(hotSongs.value)
}

// 跳转到歌曲详情页。
async function goDetail(id: number): Promise<void> {
  await router.push(`/songs/${id}`)
}

onMounted(loadRecommendations)
</script>

<style scoped>
.home-page {
  padding: var(--page-gutter);
}

.hero {
  position: relative;
  display: grid;
  min-height: 280px;
  grid-template-columns: minmax(0, 1.55fr) minmax(230px, 0.7fr);
  align-items: center;
  padding: clamp(30px, 5vw, 62px);
  overflow: hidden;
  background:
    radial-gradient(circle at 82% 40%, rgba(110, 231, 210, 0.22), transparent 26%),
    radial-gradient(circle at 92% 4%, rgba(169, 162, 255, 0.28), transparent 32%),
    linear-gradient(135deg, rgba(43, 63, 96, 0.88), rgba(26, 38, 65, 0.82));
}

.hero::after {
  position: absolute;
  right: -90px;
  bottom: -150px;
  width: 360px;
  height: 360px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 50%;
  content: '';
}

.hero-copy {
  position: relative;
  z-index: 2;
  max-width: 680px;
}

.eyebrow,
.section-heading p {
  margin: 0 0 10px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
}

.hero h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(34px, 4.2vw, 54px);
  line-height: 1.08;
  letter-spacing: -0.045em;
}

.hero-copy > p:not(.eyebrow) {
  max-width: 600px;
  margin: 18px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 11px;
  margin-top: 28px;
}

.hero-actions a,
.state-link {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  padding: 0 17px;
  border-radius: 11px;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.primary-link {
  gap: 16px;
  color: var(--text-on-accent);
  background: var(--accent);
  box-shadow: 0 10px 26px rgba(22, 186, 165, 0.2);
}

.primary-link:hover {
  background: var(--accent-strong);
  transform: translateY(-2px);
}

.secondary-link,
.state-link {
  border: 1px solid var(--border-strong);
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
}

.hero-orbit {
  position: relative;
  z-index: 1;
  display: grid;
  min-height: 220px;
  place-items: center;
}

.record {
  display: grid;
  width: 180px;
  height: 180px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 50%;
  background:
    radial-gradient(circle, var(--accent) 0 8%, #18283f 9% 16%, transparent 17%),
    repeating-radial-gradient(circle, rgba(255, 255, 255, 0.1) 0 1px, rgba(15, 25, 43, 0.9) 2px 8px);
  box-shadow: 0 32px 70px rgba(4, 10, 24, 0.36);
  transform: rotate(-12deg);
}

.record span {
  display: grid;
  width: 56px;
  height: 56px;
  place-items: center;
  border-radius: 50%;
  color: var(--text-on-accent);
  background: linear-gradient(145deg, var(--accent), var(--accent-purple));
  font-size: 22px;
}

.orbit-dot {
  position: absolute;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 22px rgba(110, 231, 210, 0.8);
}

.dot-one {
  top: 28px;
  right: 17%;
  width: 8px;
  height: 8px;
}

.dot-two {
  bottom: 24px;
  left: 12%;
  width: 5px;
  height: 5px;
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin: 36px 2px 16px;
}

.section-heading h2 {
  margin: 0;
  color: var(--text);
  font-size: 21px;
  letter-spacing: -0.025em;
}

.section-heading > span,
.section-heading > a {
  color: var(--text-muted);
  font-size: 11px;
  text-decoration: none;
}

.section-heading > a:hover {
  color: var(--accent);
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 13px;
}

.action-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 13px;
  padding: 17px;
  border: 1px solid var(--border);
  border-radius: 16px;
  color: inherit;
  background: linear-gradient(145deg, rgba(39, 56, 85, 0.72), rgba(25, 38, 61, 0.66));
  box-shadow: var(--shadow-soft);
  text-decoration: none;
}

.action-card:hover {
  border-color: var(--border-strong);
  background: linear-gradient(145deg, rgba(48, 69, 103, 0.86), rgba(29, 44, 71, 0.78));
  transform: translateY(-3px);
}

.action-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 13px;
  font-size: 19px;
}

.mint {
  color: var(--accent);
  background: var(--accent-soft);
}
.purple {
  color: var(--accent-purple);
  background: rgba(169, 162, 255, 0.13);
}
.rose {
  color: #ff9bb0;
  background: rgba(255, 155, 176, 0.12);
}
.blue {
  color: var(--accent-blue);
  background: rgba(112, 183, 255, 0.13);
}

.action-copy {
  min-width: 0;
}

.action-copy strong,
.action-copy small {
  display: block;
}

.action-copy strong {
  color: var(--text);
  font-size: 13px;
}

.action-copy small {
  margin-top: 5px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  color: var(--text-muted);
}

.action-card:hover .arrow {
  color: var(--accent);
  transform: translateX(2px);
}

.hot-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 13px;
}

.hot-card {
  position: relative;
  min-width: 0;
  padding: 10px 10px 16px;
  cursor: pointer;
}

.hot-card:hover {
  border-color: var(--border-strong);
  transform: translateY(-3px);
}

.hot-cover {
  position: relative;
  display: grid;
  min-height: 125px;
  place-items: center;
  border-radius: 13px;
  color: rgba(8, 20, 29, 0.8);
  font-size: 38px;
  font-weight: 900;
}

.hot-cover small {
  position: absolute;
  top: 10px;
  right: 11px;
  font-size: 9px;
  letter-spacing: 0.1em;
}

.tone-0 {
  background: linear-gradient(145deg, #74ead6, #6eb7f7);
}
.tone-1 {
  background: linear-gradient(145deg, #b6afff, #f1a7cc);
}
.tone-2 {
  background: linear-gradient(145deg, #f8ca7b, #f28f93);
}
.tone-3 {
  background: linear-gradient(145deg, #8bc9ff, #a8e5be);
}

.hot-info {
  min-width: 0;
  padding: 13px 5px 0;
}

.hot-info strong,
.hot-info span,
.hot-info small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hot-info strong {
  color: var(--text);
  font-size: 13px;
}
.hot-info span {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 11px;
}
.hot-info small {
  margin-top: 9px;
  color: var(--accent-strong);
  font-size: 10px;
}
.hot-info p {
  margin: 5px 0 0;
  color: var(--text-muted);
  font-size: 10px;
}

.hot-card > button {
  position: absolute;
  right: 20px;
  bottom: 18px;
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  color: var(--text-on-accent);
  background: var(--accent);
  box-shadow: 0 8px 22px rgba(22, 186, 165, 0.23);
  cursor: pointer;
  font-size: 10px;
}

.recommendation-state {
  min-height: 245px;
}

@media (max-width: 1120px) {
  .quick-actions,
  .hot-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .hero {
    display: block;
    min-height: auto;
  }

  .hero-orbit {
    display: none;
  }

  .section-heading > span {
    display: none;
  }
}

@media (max-width: 520px) {
  .quick-actions,
  .hot-grid {
    grid-template-columns: 1fr;
  }

  .hero-actions a {
    width: 100%;
  }
}
</style>
