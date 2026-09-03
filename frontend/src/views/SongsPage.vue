<!-- 音乐库页面：分页查询并按关键词、风格筛选歌曲。 -->
<template>
  <section class="songs-page">
    <PageHeader
      eyebrow="LIBRARY"
      title="音乐库"
      subtitle="按歌曲、歌手与风格浏览音乐，音频特征让每次发现更有依据"
    >
      <template #actions>
        <div class="filters">
          <el-input
            v-model="keyword"
            placeholder="搜索歌曲或歌手"
            clearable
            @clear="applyFilters"
            @keyup.enter="applyFilters"
          >
            <template #prefix>⌕</template>
          </el-input>
          <el-select v-model="genre" placeholder="全部风格" clearable @change="applyFilters">
            <el-option v-for="item in genres" :key="item" :label="item" :value="item" />
          </el-select>
          <el-button type="primary" @click="applyFilters">搜索</el-button>
        </div>
      </template>
    </PageHeader>

    <div class="library-meta">
      <span
        ><strong>{{ total }}</strong> 首歌曲</span
      >
      <button v-if="hasFilters" type="button" @click="clearFilters">清除筛选 ×</button>
    </div>

    <div v-if="loading" class="state-surface page-surface">
      <StatePanel type="loading" title="正在加载音乐库" />
    </div>
    <div v-else-if="loadFailed" class="state-surface page-surface">
      <StatePanel type="error" title="音乐库加载失败" message="服务暂时不可用，请稍后重新加载">
        <template #action
          ><el-button type="primary" @click="loadSongs">重新加载</el-button></template
        >
      </StatePanel>
    </div>
    <div v-else-if="songs.length === 0" class="state-surface page-surface">
      <StatePanel
        title="暂无歌曲"
        :message="hasFilters ? '没有匹配当前筛选条件的歌曲' : '歌曲数据导入后会展示在这里'"
      >
        <template v-if="hasFilters" #action
          ><el-button @click="clearFilters">清除筛选</el-button></template
        >
      </StatePanel>
    </div>
    <SongList v-else :songs="songs" variant="catalog" @play="play" />

    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadSongs"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { usePlayerStore } from '../stores/player'
import { listSongs, type SongSummary } from '../api/songs'
import { showError } from '../utils/feedback'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'

const pageSize = 20
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
const player = usePlayerStore()
const songs = ref<SongSummary[]>([])
const loading = ref(false)
const loadFailed = ref(false)
const page = ref(1)
const total = ref(0)
const keyword = ref('')
const genre = ref('')
const hasFilters = computed(() => keyword.value.trim().length > 0 || genre.value.length > 0)

// 播放当前页歌曲，并保留列表顺序供上一首/下一首使用。
function play(song: SongSummary): void {
  player.playSong(song)
  player.setQueue(songs.value)
}

// 按当前页和筛选条件查询歌曲；请求失败时展示可重试状态。
async function loadSongs(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    const { data } = await listSongs({
      page: page.value,
      page_size: pageSize,
      q: keyword.value.trim() || undefined,
      genre: genre.value || undefined,
    })
    songs.value = data.items
    total.value = data.total
  } catch (error) {
    songs.value = []
    total.value = 0
    loadFailed.value = true
    showError(error, '歌曲加载失败')
  } finally {
    loading.value = false
  }
}

// 筛选条件变化后回到第一页，避免新条件落在不存在的页码。
async function applyFilters(): Promise<void> {
  page.value = 1
  await loadSongs()
}

// 清空筛选并重新加载完整目录。
async function clearFilters(): Promise<void> {
  keyword.value = ''
  genre.value = ''
  await applyFilters()
}

onMounted(loadSongs)
</script>

<style scoped>
.songs-page {
  padding: var(--page-gutter);
}
.filters {
  display: grid;
  grid-template-columns: minmax(190px, 240px) 140px auto;
  gap: 9px;
  align-items: center;
}
.library-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 32px;
  margin: -12px 2px 12px;
  color: var(--text-muted);
  font-size: 11px;
}
.library-meta strong {
  color: var(--text-secondary);
  font-size: 14px;
}
.library-meta button {
  border: 0;
  color: var(--accent);
  background: transparent;
  cursor: pointer;
  font-size: 11px;
}
.state-surface {
  min-height: 310px;
}
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
@media (max-width: 680px) {
  .filters {
    width: 100%;
    grid-template-columns: minmax(0, 1fr) 112px;
  }
  .filters .el-button {
    grid-column: 1 / -1;
  }
}
</style>
