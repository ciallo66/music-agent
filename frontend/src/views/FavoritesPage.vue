<template>
  <div class="fav-page">
    <h2>我的收藏</h2>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="favSongs.length === 0" class="empty">还没有收藏任何歌曲</div>
    <div v-else class="song-list">
      <div class="song-row header">
        <span>标题</span><span>歌手</span><span>风格</span><span></span><span></span>
      </div>
      <div v-for="s in favSongs" :key="s.id" class="song-row" @click="play(s)">
        <span class="title">{{ s.title }}</span>
        <span class="artist">{{ s.artist.name }}</span>
        <span class="genre">{{ s.genre || '-' }}</span>
        <button class="play-btn" @click.stop="play(s)">▶</button>
        <button class="remove-btn" @click.stop="remove(s.id)">✕</button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref, onMounted } from 'vue'
import { listFavorites, removeFavorite } from '../api/favorites'
import { getSong, type SongDetail } from '../api/songs'
import { usePlayerStore } from '../stores/player'
const player = usePlayerStore()
const favSongs = ref<SongDetail[]>([])
const loading = ref(false)
async function load() {
  loading.value = true
  try {
    const { data } = await listFavorites()
    const songs = await Promise.all(
      data.items.map((i) =>
        getSong(i.song_id)
          .then((r) => r.data)
          .catch(() => null),
      ),
    )
    favSongs.value = songs.filter((s): s is SongDetail => s !== null)
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}
async function remove(id: number) {
  try {
    await removeFavorite(id)
    favSongs.value = favSongs.value.filter((s) => s.id !== id)
    ElMessage.success('已取消收藏')
  } catch {
    ElMessage.error('操作失败')
  }
}
function play(s: SongDetail) {
  player.playSong(s)
  player.setQueue(favSongs.value)
}
onMounted(load)
</script>
<style scoped>
.fav-page {
  padding: 40px;
}
.fav-page h2 {
  color: #f0f1f3;
  font-size: 24px;
  margin: 0 0 28px;
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
  grid-template-columns: 2fr 1.5fr 1fr 40px 40px;
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
.remove-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid #292c34;
  background: transparent;
  color: #858a96;
  cursor: pointer;
  font-size: 12px;
  display: grid;
  place-items: center;
}
.remove-btn:hover {
  border-color: #f44;
  color: #f44;
}
</style>
