<!-- 曲目管理：列表 + 新建 / 编辑 / 删除。 -->
<template>
  <section class="admin-page">
    <PageHeader title="曲目管理" subtitle="维护曲库条目的名称、歌手与流派等元数据">
      <template #actions>
        <el-button
          type="primary"
          :disabled="!auth.canManageData"
          :title="readonlyHint"
          @click="openCreate"
          >新建曲目</el-button
        >
      </template>
    </PageHeader>

    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按名称搜索"
        clearable
        style="max-width: 260px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-select
        v-model="genre"
        placeholder="全部流派"
        clearable
        style="width: 150px"
        @change="search"
      >
        <el-option v-for="item in genres" :key="item" :label="item" :value="item" />
      </el-select>
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <StatePanel v-if="loading && rows.length === 0" type="loading" title="正在读取曲目" />
    <template v-else>
      <el-table :data="rows" class="admin-table" empty-text="没有匹配的曲目">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="曲目" min-width="180" />
        <el-table-column label="歌手" min-width="130">
          <template #default="{ row }">{{ row.artist?.name ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="album" label="专辑" min-width="150" />
        <el-table-column prop="genre" label="流派" width="120" />
        <el-table-column label="节拍" width="90">
          <template #default="{ row }">{{ row.bpm ? Math.round(row.bpm) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :disabled="!auth.canManageData"
              :title="readonlyHint"
              @click="openEdit(row)"
              >编辑</el-button
            >
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="!auth.canManageData"
              :title="readonlyHint"
              @click="remove(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <span>共 {{ total }} 首</span>
        <el-pagination
          layout="prev, pager, next"
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          @current-change="changePage"
        />
      </div>
    </template>

    <el-dialog
      v-model="dialogVisible"
      :title="editing === null ? '新建曲目' : '编辑曲目'"
      width="520px"
    >
      <el-form label-position="top">
        <el-form-item label="曲目名称" required>
          <el-input v-model="form.title" maxlength="255" />
        </el-form-item>
        <el-form-item label="歌手" required>
          <el-select v-model="form.artist_id" filterable placeholder="选择歌手" style="width: 100%">
            <el-option v-for="item in artists" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="专辑">
          <el-input v-model="form.album" maxlength="255" />
        </el-form-item>
        <el-form-item label="流派">
          <el-input v-model="form.genre" maxlength="100" placeholder="例如：摇滚" />
        </el-form-item>
        <el-form-item label="时长（秒）">
          <el-input-number v-model="form.duration" :min="0" :controls="false" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import StatePanel from '../../components/StatePanel.vue'
import {
  createAdminSong,
  deleteAdminSong,
  listAdminArtists,
  listAdminSongs,
  updateAdminSong,
  type AdminArtistItem,
} from '../../api/admin'
import type { SongSummary } from '../../types/music'
import { showError, showSuccess } from '../../utils/feedback'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
// 演示账号在后台只读：按钮直接禁用并说明原因，避免点下去才收到 403
const readonlyHint = '演示账号只能查看后台数据，不能修改'

const rows = ref<SongSummary[]>([])
const artists = ref<AdminArtistItem[]>([])
const genres = ref<string[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const genre = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref<SongSummary | null>(null)

const form = reactive<{
  title: string
  artist_id: number | null
  album: string
  genre: string
  duration: number | null
}>({ title: '', artist_id: null, album: '', genre: '', duration: null })

/** 读取曲目列表；筛选条件变化时回到第一页。 */
async function load(): Promise<void> {
  loading.value = true
  try {
    const { data } = await listAdminSongs({
      q: keyword.value,
      genre: genre.value,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    showError(error, '曲目列表加载失败')
  } finally {
    loading.value = false
  }
}

function search(): void {
  page.value = 1
  void load()
}

function changePage(next: number): void {
  page.value = next
  void load()
}

function openCreate(): void {
  editing.value = null
  Object.assign(form, { title: '', artist_id: null, album: '', genre: '', duration: null })
  dialogVisible.value = true
}

function openEdit(song: SongSummary): void {
  editing.value = song
  Object.assign(form, {
    title: song.title,
    artist_id: song.artist?.id ?? null,
    album: song.album ?? '',
    genre: song.genre ?? '',
    duration: song.duration,
  })
  dialogVisible.value = true
}

async function save(): Promise<void> {
  if (!form.title.trim() || form.artist_id === null) {
    showError('曲目名称与歌手必填', '请补全必填项')
    return
  }
  saving.value = true
  const payload = {
    title: form.title.trim(),
    artist_id: form.artist_id,
    album: form.album.trim() || null,
    genre: form.genre.trim() || null,
    duration: form.duration,
  }
  try {
    if (editing.value === null) await createAdminSong(payload)
    else await updateAdminSong(editing.value.id, payload)
    showSuccess('已保存')
    dialogVisible.value = false
    await load()
  } catch (error) {
    showError(error, '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(song: SongSummary): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除「${song.title}」？该操作不可撤销。`, '删除曲目', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteAdminSong(song.id)
    showSuccess('已删除')
    await load()
  } catch (error) {
    showError(error, '删除失败')
  }
}

onMounted(async () => {
  await load()
  try {
    const { data } = await listAdminArtists({ page_size: 100 })
    artists.value = data.items
    genres.value = [...new Set(rows.value.map((item) => item.genre).filter(Boolean))] as string[]
  } catch {
    // 歌手列表失败不影响曲目列表展示
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
