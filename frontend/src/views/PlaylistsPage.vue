<template>
  <div class="playlists-page">
    <PageHeader title="我的歌单" subtitle="整理你的专属播放列表">
      <template #actions
        ><el-button type="primary" @click="showCreate = true">+ 新建歌单</el-button></template
      >
    </PageHeader>
    <StatePanel v-if="loading" type="loading" title="正在加载歌单" />
    <StatePanel
      v-else-if="playlists.length === 0"
      title="还没有歌单"
      message="创建一个歌单，开始整理喜欢的歌曲"
    />
    <div v-else class="playlist-grid">
      <div v-for="pl in playlists" :key="pl.id" class="playlist-card" @click="go(pl.id)">
        <div class="pl-cover">{{ pl.name.slice(0, 1) }}</div>
        <div class="pl-info">
          <p class="pl-name">{{ pl.name }}</p>
          <p class="pl-count">{{ pl.song_count }} 首</p>
        </div>
      </div>
    </div>
    <el-dialog v-model="showCreate" title="新建歌单" width="400px">
      <el-form :model="createForm" label-position="top">
        <el-form-item label="歌单名称">
          <el-input v-model="createForm.name" maxlength="50" placeholder="输入歌单名称" />
        </el-form-item>
        <el-form-item label="描述（可选）">
          <el-input
            v-model="createForm.description"
            maxlength="200"
            placeholder="输入描述"
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createPl">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createPlaylist, listPlaylists } from '../api/playlists'
import type { PlaylistItem } from '../api/playlists'
import { showError, showSuccess } from '../utils/feedback'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
const router = useRouter()
const playlists = ref<PlaylistItem[]>([])
const loading = ref(false)
const showCreate = ref(false)
const createForm = ref({ name: '', description: '' })
async function load() {
  loading.value = true
  try {
    const { data } = await listPlaylists()
    playlists.value = data.items
  } catch (error) {
    showError(error, '歌单加载失败')
  } finally {
    loading.value = false
  }
}
async function createPl() {
  if (!createForm.value.name.trim()) {
    showError(null, '请输入歌单名称')
    return
  }
  try {
    await createPlaylist(createForm.value)
    showSuccess('歌单创建成功')
    showCreate.value = false
    createForm.value = { name: '', description: '' }
    load()
  } catch (error) {
    showError(error, '歌单创建失败')
  }
}
function go(id: number) {
  router.push(`/playlists/${id}`)
}
onMounted(load)
</script>
<style scoped>
.playlists-page {
  padding: 40px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}
.page-header h2 {
  color: var(--text);
  font-size: 24px;
  margin: 0;
}
.loading,
.empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px 0;
}
.playlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}
.playlist-card {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 16px;
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.playlist-card:hover {
  border-color: var(--accent);
}
.pl-cover {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent), var(--accent-deep));
  display: grid;
  place-items: center;
  font-size: 20px;
  font-weight: 800;
  color: var(--text-on-accent);
  flex-shrink: 0;
}
.pl-name {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 4px;
}
.pl-count {
  color: var(--text-secondary);
  font-size: 12px;
  margin: 0;
}
</style>
