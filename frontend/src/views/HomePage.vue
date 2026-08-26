<template>
  <div class="home-page">
    <div class="hero">
      <h2>欢迎回来，{{ auth.user?.username }}</h2>
      <p>探索你的音乐世界，发现属于你的声音</p>
    </div>
    <div class="quick-actions">
      <router-link to="/songs" class="action-card">
        <span class="icon">🎵</span>
        <span class="label">音乐库</span>
      </router-link>
      <router-link to="/playlists" class="action-card">
        <span class="icon">📋</span>
        <span class="label">我的歌单</span>
      </router-link>
      <router-link to="/favorites" class="action-card">
        <span class="icon">❤️</span>
        <span class="label">收藏</span>
      </router-link>
      <router-link to="/search" class="action-card">
        <span class="icon">🔍</span>
        <span class="label">搜索</span>
      </router-link>
    </div>
    <div class="hot-section" v-if="hotSongs.length > 0">
      <h3>🔥 热门推荐</h3>
      <div class="hot-grid">
        <div v-for="s in hotSongs" :key="s.id" class="hot-card" @click="goDetail(s.id)">
          <div class="hot-cover">{{ s.title.slice(0, 1) }}</div>
          <div class="hot-info">
            <span class="hot-title">{{ s.title }}</span>
            <span class="hot-artist">{{ s.artist.name }}</span>
            <span class="hot-meta"
              >{{ s.genre || '未知风格' }} · {{ s.bpm ? Math.round(s.bpm) + ' BPM' : '' }}</span
            >
          </div>
          <button class="play-btn" @click.stop="play(s)">▶</button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listSongs, type SongSummary } from '../api/songs'
import { useAuthStore } from '../stores/auth'
import { usePlayerStore } from '../stores/player'
const auth = useAuthStore()
const router = useRouter()
const player = usePlayerStore()
const hotSongs = ref<SongSummary[]>([])
onMounted(async () => {
  try {
    const { data } = await listSongs({ page_size: 8 })
    hotSongs.value = data.items
  } catch {
    hotSongs.value = []
  }
})
function play(s: SongSummary) {
  player.playSong(s)
  player.setQueue(hotSongs.value)
}
function goDetail(id: number) {
  router.push(`/songs/${id}`)
}
</script>
<style scoped>
.home-page {
  padding: 40px;
}
.hero {
  margin-bottom: 40px;
}
.hero h2 {
  color: #f0f1f3;
  font-size: 28px;
  margin: 0 0 8px;
}
.hero p {
  color: #858a96;
  font-size: 15px;
  margin: 0;
}
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 40px;
}
.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 20px;
  background: #111215;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  text-decoration: none;
  transition: border-color 0.2s;
}
.action-card:hover {
  border-color: #59e2a4;
}
.icon {
  font-size: 32px;
}
.label {
  color: #c9cbd2;
  font-size: 14px;
}
.hot-section h3 {
  color: #f0f1f3;
  font-size: 20px;
  margin: 0 0 16px;
}
.hot-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.hot-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #111215;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.hot-card:hover {
  border-color: #59e2a4;
}
.hot-cover {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2a8f6e, #59e2a4);
  display: grid;
  place-items: center;
  color: #07110c;
  font-weight: 800;
  font-size: 18px;
  flex-shrink: 0;
}
.hot-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.hot-title {
  color: #f0f1f3;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hot-artist {
  color: #59e2a4;
  font-size: 12px;
}
.hot-meta {
  color: #626771;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.play-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: #59e2a4;
  color: #07110c;
  cursor: pointer;
  font-size: 12px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
@media (max-width: 1024px) {
  .hot-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 768px) {
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
  .hot-grid {
    grid-template-columns: 1fr;
  }
}
</style>
