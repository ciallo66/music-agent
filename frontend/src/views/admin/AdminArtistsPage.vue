<!-- 歌手管理：列表 + 新建 / 重命名 / 删除。 -->
<template>
  <section class="admin-page">
    <PageHeader title="歌手管理" subtitle="维护曲库中的歌手条目">
      <template #actions>
        <el-button
          type="primary"
          :disabled="!auth.canManageData"
          :title="readonlyHint"
          @click="openCreate"
          >新建歌手</el-button
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
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <StatePanel v-if="loading && rows.length === 0" type="loading" title="正在读取歌手" />
    <template v-else>
      <el-table :data="rows" class="admin-table" empty-text="没有匹配的歌手">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="歌手" min-width="200" />
        <el-table-column prop="avatar_url" label="头像地址" min-width="220" />
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
        <span>共 {{ total }} 位</span>
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
      :title="editing === null ? '新建歌手' : '编辑歌手'"
      width="460px"
    >
      <el-form label-position="top">
        <el-form-item label="歌手名称" required>
          <el-input v-model="form.name" maxlength="255" />
        </el-form-item>
        <el-form-item label="头像地址">
          <el-input v-model="form.avatar_url" maxlength="500" placeholder="可留空" />
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
  createAdminArtist,
  deleteAdminArtist,
  listAdminArtists,
  updateAdminArtist,
  type AdminArtistItem,
} from '../../api/admin'
import { showError, showSuccess } from '../../utils/feedback'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
// 演示账号在后台只读：按钮直接禁用并说明原因，避免点下去才收到 403
const readonlyHint = '演示账号只能查看后台数据，不能修改'

const rows = ref<AdminArtistItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref<AdminArtistItem | null>(null)
const form = reactive({ name: '', avatar_url: '' })

async function load(): Promise<void> {
  loading.value = true
  try {
    const { data } = await listAdminArtists({
      q: keyword.value,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    showError(error, '歌手列表加载失败')
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
  form.name = ''
  form.avatar_url = ''
  dialogVisible.value = true
}

function openEdit(artist: AdminArtistItem): void {
  editing.value = artist
  form.name = artist.name
  form.avatar_url = artist.avatar_url ?? ''
  dialogVisible.value = true
}

async function save(): Promise<void> {
  if (!form.name.trim()) {
    showError('歌手名称必填')
    return
  }
  saving.value = true
  const payload = { name: form.name.trim(), avatar_url: form.avatar_url.trim() || null }
  try {
    if (editing.value === null) await createAdminArtist(payload)
    else await updateAdminArtist(editing.value.id, payload)
    showSuccess('已保存')
    dialogVisible.value = false
    await load()
  } catch (error) {
    showError(error, '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(artist: AdminArtistItem): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除歌手「${artist.name}」？`, '删除歌手', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteAdminArtist(artist.id)
    showSuccess('已删除')
    await load()
  } catch (error) {
    showError(error, '删除失败')
  }
}

onMounted(load)
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
