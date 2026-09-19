<!-- 账号管理：搜索、分页、切换角色与状态。 -->
<template>
  <section class="admin-page">
    <PageHeader title="账号管理" subtitle="查看全部账号，并调整角色与启用状态">
      <template #actions>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </template>
    </PageHeader>

    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按用户名搜索"
        clearable
        style="max-width: 260px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <StatePanel v-if="loading && rows.length === 0" type="loading" title="正在读取账号列表" />
    <template v-else>
      <el-table :data="rows" class="admin-table" empty-text="没有匹配的账号">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'warning' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="favorites" label="收藏" width="80" />
        <el-table-column prop="playlists" label="歌单" width="80" />
        <el-table-column prop="feedback" label="反馈" width="80" />
        <el-table-column label="注册时间" min-width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :disabled="busyId === row.id || !auth.canManageData"
              :title="auth.canManageData ? undefined : readonlyHint"
              @click="toggleRole(row)"
            >
              {{ row.role === 'admin' ? '降为普通' : '设为管理员' }}
            </el-button>
            <el-button
              size="small"
              type="danger"
              plain
              :disabled="busyId === row.id || !auth.canManageData"
              :title="auth.canManageData ? undefined : readonlyHint"
              @click="toggleStatus(row)"
            >
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <span>共 {{ total }} 个账号</span>
        <el-pagination
          layout="prev, pager, next"
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          @current-change="changePage"
        />
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHeader from '../../components/PageHeader.vue'
import StatePanel from '../../components/StatePanel.vue'
import { listAdminUsers, updateAdminUser, type AdminUserItem } from '../../api/admin'
import { showError, showSuccess } from '../../utils/feedback'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
// 演示账号在后台只读：按钮直接禁用并说明原因，避免点下去才收到 403
const readonlyHint = '演示账号只能查看后台数据，不能修改'

const rows = ref<AdminUserItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)
const busyId = ref<number | null>(null)

async function load(): Promise<void> {
  loading.value = true
  try {
    const { data } = await listAdminUsers({
      keyword: keyword.value,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    showError(error, '账号列表加载失败')
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

/** 修改一位账号的角色或状态，成功后用返回结果刷新列表。 */
async function patch(
  user: AdminUserItem,
  payload: { role?: string; status?: string },
): Promise<void> {
  busyId.value = user.id
  try {
    const { data } = await updateAdminUser(user.id, payload, {
      keyword: keyword.value,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = data.items
    total.value = data.total
    showSuccess('已更新')
  } catch (error) {
    showError(error, '更新失败')
  } finally {
    busyId.value = null
  }
}

function toggleRole(user: AdminUserItem): void {
  void patch(user, { role: user.role === 'admin' ? 'user' : 'admin' })
}

function toggleStatus(user: AdminUserItem): void {
  void patch(user, { status: user.status === 'active' ? 'disabled' : 'active' })
}

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.admin-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text-secondary);
  --el-table-header-text-color: var(--text-muted);
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
