<template>
  <div class="search-page">
    <h2>搜索</h2>
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索歌曲、歌手"
        clearable
        @keyup.enter="doSearch"
        style="max-width: 500px"
        size="large"
      />
      <el-button type="primary" size="large" @click="doSearch">搜索</el-button>
    </div>
    <div v-if="loading" class="loading">搜索中...</div>
    <div v-else-if="results.length === 0 && searched" class="empty">没有找到相关歌曲</div>
    <div v-else-if="results.length > 0" class="song-list">
      <div class="song-row header">
        <span>标题</span><span>歌手</span><span>风格</span><span>BPM</span><span></span>
      </div>
      <div v-for="s in results" :key="s.id" class="song-row" @click="play(s)">
        <span class="title">{{ s.title }}</span>
        <span class="artist">{{ s.artist.name }}</span>
        <span class="genre">{{ s.genre || '-' }}</span>
        <span>{{ s.bpm ? Math.round(s.bpm) : '-' }}</span>
        <button class="play-btn" @click.stop="play(s)">▶</button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { listSongs } from '../api/songs'
import type { SongSummary } from '../api/songs'
import { usePlayerStore } from '../stores/player'
const player = usePlayerStore()
const keyword = ref('')
const results = ref<SongSummary[]>([])
const loading = ref(false)
const searched = ref(false)
async function doSearch() {
  if (!keyword.value.trim()) return
  loading.value = true
  searched.value = true
  try {
    const { data } = await listSongs({ q: keyword.value, page_size: 50 })
    results.value = data.items
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}
function play(s: SongSummary) {
  player.playSong(s)
  player.setQueue(results.value)
}
</script>
<style scoped>
.search-page {
  padding: 40px;
}
.search-page h2 {
  color: #f0f1f3;
  font-size: 24px;
  margin: 0 0 24px;
}
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 28px;
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
  grid-template-columns: 2fr 1.5fr 1fr 60px 40px;
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
.genre {
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
