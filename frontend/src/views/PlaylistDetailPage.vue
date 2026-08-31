<template>
  <div class="detail-page" v-if="playlist">
    <div class="page-header legacy-header">
      <button class="back-btn" @click="router.back()">← 返回</button>
      <div class="pl-info">
        <h2>{{ playlist.name }}</h2>
        <p class="desc">{{ playlist.description || '无描述' }}</p>
        <p class="meta">{{ playlist.song_count }} 首歌曲</p>
      </div>
    </div>
    <StatePanel
      v-if="playlist.songs.length === 0"
      title="歌单里还没有歌曲"
      message="去音乐库添加一些歌曲吧"
    />
    <SongList v-else :songs="playlist.songs" variant="playlist" @play="play" />
  </div>
  <StatePanel v-else type="loading" title="正在加载歌单" />
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
async function load() {
  try {
    const { data } = await getPlaylist(Number(route.params.id))
    playlist.value = data
  } catch (error) {
    showError(error, '歌单加载失败')
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
  padding: 40px;
}
.page-header {
  margin-bottom: 28px;
}
.back-btn {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 0;
}
.pl-info h2 {
  color: var(--text);
  font-size: 28px;
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
  margin: 0;
}
</style>
