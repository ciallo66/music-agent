<template>
  <div class="fav-page">
    <PageHeader title="我的收藏" subtitle="收藏的歌曲会出现在这里" />
    <StatePanel v-if="loading" type="loading" title="正在加载收藏" />
    <StatePanel
      v-else-if="favSongs.length === 0"
      title="还没有收藏任何歌曲"
      message="在歌曲详情页点击收藏即可添加"
    />
    <SongList v-else :songs="favSongs" variant="favorites" @play="play" @remove="remove" />
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listFavorites, removeFavorite } from '../api/favorites'
import { getSong, type SongDetail, type SongSummary } from '../api/songs'
import { usePlayerStore } from '../stores/player'
import { showError, showSuccess } from '../utils/feedback'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'
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
  } catch (error) {
    showError(error, '收藏加载失败')
  } finally {
    loading.value = false
  }
}
async function remove(id: number) {
  try {
    await removeFavorite(id)
    favSongs.value = favSongs.value.filter((s) => s.id !== id)
    showSuccess('已取消收藏')
  } catch (error) {
    showError(error, '取消收藏失败')
  }
}
function play(s: SongSummary) {
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
  color: var(--text);
  font-size: 24px;
  margin: 0 0 28px;
}
</style>
