<template>
  <div class="songs-page">
    <div class="page-header">
      <h2>音乐库</h2>
      <div class="filters">
        <el-input
          v-model="keyword"
          placeholder="搜索歌曲/歌手"
          clearable
          @clear="loadSongs"
          @keyup.enter="loadSongs"
          style="width: 220px"
        />
        <el-select
          v-model="genre"
          placeholder="风格"
          clearable
          @change="loadSongs"
          style="width: 140px"
        >
          <el-option v-for="g in genres" :key="g" :label="g" :value="g" />
        </el-select>
        <el-button @click="loadSongs">搜索</el-button>
      </div>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="songs.length === 0" class="empty">暂无歌曲</div>
    <div v-else class="song-list">
      <div class="song-row header">
        <span>标题</span><span>歌手</span><span>风格</span><span>BPM</span><span>Energy</span
        ><span>Valence</span><span></span>
      </div>
      <div v-for="song in songs" :key="song.id" class="song-row" @click="play(song)">
        <span class="title">{{ song.title }}</span>
        <span class="artist">{{ song.artist.name }}</span>
        <span class="genre">{{ song.genre || '-' }}</span>
        <span>{{ song.bpm ? Math.round(song.bpm) : '-' }}</span>
        <span>{{ song.energy !== null ? (song.energy * 100).toFixed(0) + '%' : '-' }}</span>
        <span>{{ song.valence !== null ? (song.valence * 100).toFixed(0) + '%' : '-' }}</span>
        <button class="play-btn" @click.stop="play(song)">▶</button>
      </div>
    </div>
    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadSongs"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player'
import { listSongs, type SongSummary } from '../api/songs'
const player = usePlayerStore()
const songs = ref<SongSummary[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const keyword = ref('')
const genre = ref('')
const genres = [
  'Pop',
  'Rock',
  'Electronic',
  'Jazz',
  'Classical',
  'Hip-Hop',
  'R&B',
  'Country',
  'Folk',
  'Metal',
]
function play(s: SongSummary) {
  player.playSong(s)
  player.setQueue(songs.value)
}
async function loadSongs() {
  loading.value = true
  try {
    const { data } = await listSongs({
      page: page.value,
      page_size: 20,
      q: keyword.value || undefined,
      genre: genre.value || undefined,
    })
    songs.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}
onMounted(loadSongs)
</script>
<style scoped>
.songs-page {
  padding: 40px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  flex-wrap: wrap;
  gap: 16px;
}
.page-header h2 {
  color: #f0f1f3;
  font-size: 24px;
  margin: 0;
}
.filters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
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
  grid-template-columns: 2fr 1.5fr 1fr 60px 70px 70px 40px;
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
  padding: 8px 16px;
}
.song-row.header:hover {
  background: transparent;
}
.title {
  color: #f0f1f3;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
