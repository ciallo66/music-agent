<!-- 搜索页面：提交关键词并展示可查看详情的结果列表。 -->
<template>
  <section class="search-page">
    <PageHeader
      eyebrow="DISCOVER"
      title="搜索内容"
      subtitle="输入歌曲名、歌手或关键词，快速定位想听的声音"
    />
    <form class="search-panel page-surface" @submit.prevent="doSearch">
      <span class="search-icon" aria-hidden="true">⌕</span>
      <el-input
        v-model="keyword"
        placeholder="搜索歌曲或歌手…"
        clearable
        size="large"
        @clear="resetSearch"
      />
      <el-button
        native-type="submit"
        type="primary"
        size="large"
        :loading="loading"
        :disabled="keyword.trim().length === 0"
        >搜索</el-button
      >
    </form>

    <div v-if="!searched && !loading" class="search-guide page-surface">
      <div class="guide-visual" aria-hidden="true"><span>♫</span><i></i></div>
      <div class="guide-copy">
        <p>SEARCH YOUR SOUND</p>
        <h2>从一个关键词开始</h2>
        <span>可以搜索标题、来源和标签，结果可进入详情页查看结构化信息。</span>
        <div class="suggestions">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion"
            type="button"
            @click="searchSuggestion(suggestion)"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>
    </div>
    <div v-else-if="loading" class="result-state page-surface">
      <StatePanel type="loading" title="正在搜索" />
    </div>
    <div v-else-if="loadFailed" class="result-state page-surface">
      <StatePanel type="error" title="搜索失败" message="服务暂时不可用，请稍后重新搜索">
        <template #action
          ><el-button type="primary" @click="doSearch">重新搜索</el-button></template
        >
      </StatePanel>
    </div>
    <div v-else-if="results.length === 0 && searched" class="result-state page-surface">
      <StatePanel
        title="没有找到相关歌曲"
        :message="`没有与“${lastKeyword}”匹配的结果，试试更短的关键词或其他拼写`"
      />
    </div>
    <div v-else-if="results.length" class="results">
      <div class="result-heading">
        <strong>搜索结果</strong><span>共 {{ results.length }} 首</span>
      </div>
      <SongList :songs="results" variant="search" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { listSongs, type SongSummary } from '../api/songs'
import { showError } from '../utils/feedback'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'

const suggestions = ['流行', '摇滚', '爵士', '电子']
const keyword = ref('')
const lastKeyword = ref('')
const results = ref<SongSummary[]>([])
const loading = ref(false)
const searched = ref(false)
const loadFailed = ref(false)

// 提交非空关键词并保存最后一次查询，用于空结果提示。
async function doSearch(): Promise<void> {
  const query = keyword.value.trim()
  if (!query || loading.value) return
  loading.value = true
  searched.value = true
  loadFailed.value = false
  lastKeyword.value = query
  try {
    const { data } = await listSongs({ q: query, page_size: 50 })
    results.value = data.items
  } catch (error) {
    results.value = []
    loadFailed.value = true
    showError(error, '搜索失败')
  } finally {
    loading.value = false
  }
}

// 将推荐关键词写入输入框并复用统一搜索流程。
async function searchSuggestion(suggestion: string): Promise<void> {
  keyword.value = suggestion
  await doSearch()
}

// 清除输入时同时重置结果和搜索状态。
function resetSearch(): void {
  searched.value = false
  loadFailed.value = false
  lastKeyword.value = ''
  results.value = []
}
</script>

<style scoped>
.search-page {
  padding: var(--page-gutter);
}
.search-panel {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  max-width: 880px;
  padding: 13px 14px 13px 19px;
}
.search-icon {
  color: var(--accent);
  font-size: 24px;
}
.search-guide {
  display: grid;
  min-height: 330px;
  grid-template-columns: 0.75fr 1.25fr;
  align-items: center;
  gap: clamp(24px, 5vw, 70px);
  margin-top: 20px;
  padding: clamp(30px, 5vw, 60px);
  overflow: hidden;
}
.guide-visual {
  position: relative;
  display: grid;
  width: min(220px, 100%);
  aspect-ratio: 1;
  place-items: center;
  justify-self: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  background: repeating-radial-gradient(
    circle,
    rgba(255, 255, 255, 0.1) 0 1px,
    rgba(22, 35, 57, 0.9) 2px 9px
  );
  box-shadow: 0 26px 60px rgba(4, 10, 24, 0.3);
}
.guide-visual span {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  border-radius: 50%;
  color: var(--text-on-accent);
  background: linear-gradient(145deg, var(--accent), var(--accent-purple));
  font-size: 24px;
}
.guide-visual i {
  position: absolute;
  right: -18px;
  top: 16%;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 24px var(--accent);
}
.guide-copy > p {
  margin: 0 0 10px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
}
.guide-copy h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(24px, 3vw, 36px);
  letter-spacing: -0.04em;
}
.guide-copy > span {
  display: block;
  max-width: 520px;
  margin-top: 13px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.8;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
}
.suggestions button {
  padding: 8px 13px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.035);
  cursor: pointer;
  font-size: 11px;
}
.suggestions button:hover {
  border-color: var(--accent);
  color: var(--accent-strong);
  background: var(--accent-soft);
}
.result-state {
  min-height: 320px;
  margin-top: 20px;
}
.results {
  margin-top: 24px;
}
.result-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 3px 12px;
}
.result-heading strong {
  color: var(--text);
  font-size: 14px;
}
.result-heading span {
  color: var(--text-muted);
  font-size: 10px;
}
@media (max-width: 700px) {
  .search-guide {
    grid-template-columns: 1fr;
    text-align: center;
  }
  .guide-visual {
    width: 145px;
  }
  .suggestions {
    justify-content: center;
  }
}
@media (max-width: 520px) {
  .search-panel {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .search-panel .el-button {
    grid-column: 1 / -1;
  }
}
</style>
