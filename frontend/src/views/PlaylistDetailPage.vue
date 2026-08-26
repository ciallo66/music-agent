<template>
  <div class="detail-page" v-if="playlist">
    <div class="page-header">
      <button class="back-btn" @click="router.back()">← 返回</button>
      <div class="pl-info">
        <h2>{{ playlist.name }}</h2>
        <p class="desc">{{ playlist.description || '无描述' }}</p>
        <p class="meta">{{ playlist.song_count }} 首歌曲</p>
      </div>
    </div>
    <div v-if="playlist.songs.length === 0" class="empty">歌单里还没有歌曲</div>
    <div v-else class="song-list">
      <div class="song-row header">
        <span>标题</span><span>歌手</span><span>时长</span><span></span>
      </div>
      <div v-for="song in playlist.songs" :key="song.id" class="song-row" @click="play(song)">
        <span class="title">{{ song.title }}</span>
        <span class="artist">{{ song.artist.name }}</span>
        <span class="dur">{{ song.duration ? formatDur(song.duration) : '-' }}</span>
        <button class="play-btn" @click.stop="play(song)">▶</button>
      </div>
    </div>
  </div>
  <div v-else class="loading">加载中...</div>
</template>
<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPlaylist } from '../api/playlists'
import type { PlaylistDetail, SongBrief } from '../api/playlists'
import { usePlayerStore } from '../stores/player'
const route = useRoute()
const router = useRouter()
const player = usePlayerStore()
const playlist = ref<PlaylistDetail | null>(null)
async function load() {
  try {
    const { data } = await getPlaylist(Number(route.params.id))
    playlist.value = data
  } catch {
    ElMessage.error('加载失败')
  }
}
function play(s: SongBrief) {
  player.playSong(s)
  if (playlist.value) player.setQueue(playlist.value.songs)
}
function formatDur(s: number) {
  const m = Math.floor(s / 60)
  const sec = (s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
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
  color: #59e2a4;
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 0;
}
.pl-info h2 {
  color: #f0f1f3;
  font-size: 28px;
  margin: 0 0 6px;
}
.desc {
  color: #858a96;
  font-size: 14px;
  margin: 0 0 4px;
}
.meta {
  color: #626771;
  font-size: 13px;
  margin: 0;
}
.loading,
.empty {
  text-align: center;
  color: #858a96;
  padding: 60px 0;
}
.song-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.song-row {
  display: grid;
  grid-template-columns: 2fr 1.5fr 80px 40px;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
}
.song-row:hover {
  background: #14161b;
}
.song-row.header {
  cursor: default;
  color: #626771;
  font-size: 12px;
}
.song-row.header:hover {
  background: transparent;
}
.title {
  color: #f0f1f3;
  font-size: 14px;
}
.artist,
.dur {
  color: #858a96;
  font-size: 13px;
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
}
</style>
