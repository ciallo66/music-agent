<template>
  <div class="songs-page">
    <PageHeader title="音乐库" subtitle="按风格、语言和歌手探索歌曲">
      <template #actions>
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
      </template>
    </PageHeader>
    <StatePanel v-if="loading" type="loading" title="正在加载音乐库" />
    <StatePanel
      v-else-if="songs.length === 0"
      title="暂无歌曲"
      message="可以尝试更换搜索关键词或筛选条件"
    />
    <SongList v-else :songs="songs" variant="catalog" @play="play" />
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
import { ref, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player'
import { listSongs, type SongSummary } from '../api/songs'
import { showError } from '../utils/feedback'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'
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
  } catch (error) {
    showError(error, '歌曲加载失败')
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
  color: var(--text);
  font-size: 24px;
  margin: 0;
}
.filters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
