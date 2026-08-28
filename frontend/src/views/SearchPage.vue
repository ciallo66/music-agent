<template>
  <div class="search-page">
    <PageHeader title="搜索" subtitle="搜索歌曲名称或歌手" />
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
    <StatePanel v-if="loading" type="loading" title="正在搜索" />
    <StatePanel
      v-else-if="results.length === 0 && searched"
      title="没有找到相关歌曲"
      message="试试更短的关键词或其他拼写"
    />
    <SongList v-else-if="results.length > 0" :songs="results" variant="search" @play="play" />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { listSongs } from '../api/songs'
import type { SongSummary } from '../api/songs'
import { usePlayerStore } from '../stores/player'
import { showError } from '../utils/feedback'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'
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
  } catch (error) {
    results.value = []
    showError(error, '搜索失败')
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
  color: var(--text);
  font-size: 24px;
  margin: 0 0 24px;
}
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 28px;
}
</style>
