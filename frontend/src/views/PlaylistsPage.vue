<!-- 内容集合页面：查询、创建并进入用户集合。 -->
<template>
  <section class="playlists-page">
    <PageHeader
      eyebrow="内容集合"
      title="我的空间"
      subtitle="把关注的内容整理成适合不同场景的专属集合"
    >
      <template #actions
        ><el-button type="primary" @click="showCreate = true">＋ 新建歌单</el-button></template
      >
    </PageHeader>

    <!-- 加载慢（>150ms）才显示骨架，避免骨架一闪就被真实内容替换 -->
    <SkeletonList v-if="showSkeleton" :rows="5" variant="card" status="正在加载内容集合" />
    <div v-else-if="loadFailed" class="state-surface page-surface">
      <StatePanel type="error" title="歌单加载失败" message="服务暂时不可用，请稍后重试">
        <template #action><el-button type="primary" @click="load">重新加载</el-button></template>
      </StatePanel>
    </div>
    <div v-else-if="playlists.length === 0 && !loading" class="state-surface page-surface">
      <StatePanel title="还没有歌单" message="创建一个歌单，开始整理喜欢的歌曲">
        <template #action
          ><el-button type="primary" @click="showCreate = true">创建第一个歌单</el-button></template
        >
      </StatePanel>
    </div>
    <div v-else class="playlist-grid">
      <article
        v-for="playlist in playlists"
        :key="playlist.id"
        class="playlist-card page-surface"
        role="button"
        tabindex="0"
        @click="go(playlist.id)"
        @keydown.enter="go(playlist.id)"
        @keydown.space.prevent="go(playlist.id)"
      >
        <div class="cover">
          <span>{{ playlist.name.slice(0, 1) }}</span
          ><small>歌单</small>
        </div>
        <div class="playlist-copy">
          <strong>{{ playlist.name }}</strong>
          <span>{{ playlist.song_count }} 首歌曲</span>
          <p>{{ playlist.description || '还没有添加描述' }}</p>
        </div>
        <span class="open-mark" aria-hidden="true">→</span>
      </article>
      <button class="create-card" type="button" @click="showCreate = true">
        <span>＋</span><strong>新建歌单</strong><small>创建新的音乐收藏</small>
      </button>
    </div>

    <el-dialog v-model="showCreate" title="新建歌单" width="420px" @closed="resetForm">
      <el-form :model="createForm" label-position="top" @submit.prevent="createPl">
        <el-form-item label="歌单名称">
          <el-input
            v-model="createForm.name"
            maxlength="50"
            show-word-limit
            placeholder="例如：夜晚放松"
            autofocus
            @keyup.enter="createPl"
          />
        </el-form-item>
        <el-form-item label="描述（可选）">
          <el-input
            v-model="createForm.description"
            maxlength="200"
            show-word-limit
            :rows="3"
            placeholder="简单描述这个歌单适合的场景"
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="creating" @click="showCreate = false">取消</el-button>
        <el-button
          type="primary"
          :loading="creating"
          :disabled="createForm.name.trim().length === 0"
          @click="createPl"
          >创建歌单</el-button
        >
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createPlaylist, listPlaylists, type PlaylistItem } from '../api/playlists'
import { showError, showSuccess } from '../utils/feedback'
import { useDelayedFlag } from '../composables/useDelayedFlag'
import PageHeader from '../components/PageHeader.vue'
import SkeletonList from '../components/SkeletonList.vue'
import StatePanel from '../components/StatePanel.vue'

const router = useRouter()
const playlists = ref<PlaylistItem[]>([])
const loading = ref(false)
// 只有加载超过 150ms 才显示骨架，响应快时不出占位
const showSkeleton = useDelayedFlag(loading)
const loadFailed = ref(false)
const creating = ref(false)
const showCreate = ref(false)
const createForm = reactive({ name: '', description: '' })

// 查询当前用户歌单，并把失败显式转换为页面状态。
async function load(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  try {
    const { data } = await listPlaylists()
    playlists.value = data.items
  } catch (error) {
    playlists.value = []
    loadFailed.value = true
    showError(error, '歌单加载失败')
  } finally {
    loading.value = false
  }
}

// 校验并创建歌单；成功后等待列表刷新，保证页面立即反映新数据。
async function createPl(): Promise<void> {
  const name = createForm.name.trim()
  if (!name || creating.value) return
  creating.value = true
  try {
    await createPlaylist({ name, description: createForm.description.trim() || undefined })
    showSuccess('歌单创建成功')
    showCreate.value = false
    await load()
  } catch (error) {
    showError(error, '歌单创建失败')
  } finally {
    creating.value = false
  }
}

// 弹窗关闭后清理表单，避免下次打开残留上次输入。
function resetForm(): void {
  createForm.name = ''
  createForm.description = ''
}

// 进入指定歌单详情。
async function go(id: number): Promise<void> {
  await router.push(`/playlists/${id}`)
}

onMounted(load)
</script>

<style scoped>
.playlists-page {
  padding: var(--page-gutter);
}
.state-surface {
  min-height: 330px;
}
.playlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(265px, 1fr));
  gap: 14px;
}
.playlist-card {
  position: relative;
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr) auto;
  align-items: center;
  gap: 15px;
  min-height: 112px;
  padding: 14px;
  cursor: pointer;
}
.playlist-card:hover {
  border-color: var(--border-strong);
  background: var(--surface-hover);
}
/* 歌单没有专辑图，也不编造渐变封面：一块中性底 + 首字，信息更准确 */
.cover {
  display: flex;
  width: 72px;
  height: 72px;
  align-items: flex-start;
  justify-content: space-between;
  flex-direction: column;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  background: var(--surface-raised);
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
}
.cover small {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.04em;
}
.playlist-copy {
  min-width: 0;
}
.playlist-copy strong,
.playlist-copy span,
.playlist-copy p {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.playlist-copy strong {
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 500;
}
.playlist-copy span {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.playlist-copy p {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.open-mark {
  color: var(--text-muted);
}
.playlist-card:hover .open-mark {
  color: var(--accent);
  transform: translateX(2px);
}
.create-card {
  display: flex;
  min-height: 112px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 4px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
}
.create-card span {
  color: var(--text-muted);
  font-size: 20px;
}
.create-card strong {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: 500;
}
.create-card small {
  font-size: var(--fs-xs);
}
.create-card:hover {
  border-color: var(--border-strong);
  background: var(--surface);
  color: var(--text-secondary);
}
@media (max-width: 520px) {
  .playlist-grid {
    grid-template-columns: 1fr;
  }
}
</style>
