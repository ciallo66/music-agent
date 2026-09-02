<template>
  <section v-if="playlist" class="detail-page">
    <div class="page-header legacy-header">
      <button class="back-btn" type="button" @click="router.back()">← 返回歌单</button>
      <div class="pl-info">
        <h2>{{ playlist.name }}</h2>
        <p class="desc">{{ playlist.description || '还没有添加描述' }}</p>
        <p class="meta"><span>PLAYLIST</span>{{ playlist.song_count }} 首歌曲</p>
      </div>
    </div>
    <StatePanel
      v-if="playlist.songs.length === 0"
      title="歌单里还没有歌曲"
      message="去音乐库添加一些歌曲吧"
    />
    <SongList v-else :songs="playlist.songs" variant="playlist" @play="play" />
  </section>
  <section v-else class="detail-page">
    <div class="state-surface page-surface">
      <StatePanel v-if="loading" type="loading" title="正在加载歌单" />
      <StatePanel
        v-else
        type="error"
        title="歌单加载失败"
        message="歌单可能不存在，或你暂时没有访问权限"
      >
        <template #action
          ><el-button type="primary" @click="router.push('/playlists')"
            >返回我的歌单</el-button
          ></template
        >
      </StatePanel>
    </div>
  </section>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPlaylist } from '../api/playlists'
import type { PlaylistDetail, SongSummary } from '../types/music'
import { usePlayerStore } from '../stores/player'
import { showError } from '../utils/feedback'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'
const route = useRoute()
const router = useRouter()
const player = usePlayerStore()
const playlist = ref<PlaylistDetail | null>(null)
const loading = ref(false)
async function load() {
  loading.value = true
  try {
    const { data } = await getPlaylist(Number(route.params.id))
    playlist.value = data
  } catch (error) {
    showError(error, '歌单加载失败')
  } finally {
    loading.value = false
  }
}
function play(s: SongSummary) {
  player.playSong(s)
  if (playlist.value) player.setQueue(playlist.value.songs)
}
onMounted(load)
</script>
<style scoped>
.detail-page {
  padding: var(--page-gutter);
}
.page-header {
  margin-bottom: 24px;
  padding: clamp(24px, 4vw, 42px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background:
    radial-gradient(circle at 92% 20%, rgba(110, 231, 210, 0.18), transparent 26%),
    linear-gradient(145deg, rgba(42, 60, 91, 0.8), rgba(25, 38, 62, 0.72));
  box-shadow: var(--shadow-soft);
}
.back-btn {
  background: none;
  border: none;
  color: var(--accent-strong);
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 0;
}
.pl-info h2 {
  color: var(--text);
  font-size: clamp(28px, 4vw, 42px);
  letter-spacing: -0.04em;
  margin: 0 0 6px;
}
.desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 4px;
}
.meta {
  color: var(--text-muted);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 0 0;
}
.meta span {
  color: var(--accent);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.16em;
}
.state-surface {
  min-height: 360px;
}
</style>
