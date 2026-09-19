<!-- 管理员导入任务页面：提交任务并轮询展示进度与失败原因。 -->
<template>
  <div class="admin-imports-page">
    <PageHeader title="导入任务" subtitle="管理 Jamendo 音乐元数据导入任务">
      <template #actions>
        <el-button
          type="primary"
          :disabled="!auth.canManageData"
          :title="auth.canManageData ? undefined : readonlyHint"
          @click="dialogVisible = true"
          >新建导入任务</el-button
        >
      </template>
    </PageHeader>

    <div class="notice-card">
      <span class="notice-icon" aria-hidden="true">↗</span>
      <div>
        <strong>只导入元数据</strong>
        <p>任务会保存歌曲信息和合法外链，不下载或托管音频。运行中的任务会自动刷新进度。</p>
      </div>
    </div>

    <StatePanel v-if="loading && jobs.length === 0" type="loading" title="正在加载导入任务" />
    <StatePanel
      v-else-if="jobs.length === 0"
      title="暂无导入任务"
      message="点击右上角新建任务，先导入 100 条数据进行验收"
    />
    <el-table v-else :data="jobs" class="jobs-table" stripe>
      <el-table-column label="任务" min-width="190">
        <template #default="{ row }">
          <div class="job-name">Jamendo #{{ row.id }}</div>
          <div class="muted">创建于 {{ formatDate(row.created_at) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" effect="dark">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" min-width="220">
        <template #default="{ row }">
          <el-progress
            :percentage="progress(row)"
            :status="
              row.status === 'failed'
                ? 'exception'
                : row.status === 'completed'
                  ? 'success'
                  : undefined
            "
            :stroke-width="8"
          />
          <div class="muted">已获取 {{ row.fetched }} / {{ row.requested_limit }} 条</div>
        </template>
      </el-table-column>
      <el-table-column label="处理结果" min-width="180">
        <template #default="{ row }">
          <span class="result-count">新增 {{ row.created }}</span>
          <span class="result-count">更新 {{ row.updated }}</span>
          <span class="result-count">跳过 {{ row.skipped }}</span>
        </template>
      </el-table-column>
      <el-table-column label="失败原因" min-width="180">
        <template #default="{ row }">
          <span v-if="row.error_message" class="error-text">{{ row.error_message }}</span>
          <span v-else-if="failureSummary(row)" class="error-text">{{ failureSummary(row) }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="完成时间" width="180">
        <template #default="{ row }">
          <span class="muted">{{ row.finished_at ? formatDate(row.finished_at) : '执行中' }}</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建 Jamendo 导入任务" width="420px" destroy-on-close>
      <el-form label-position="top" @submit.prevent="createJob">
        <el-form-item label="导入数量">
          <el-input-number
            v-model="form.limit"
            :min="1"
            :max="10000"
            :step="100"
            controls-position="right"
          />
          <div class="field-help">建议先使用 100 条进行真实链路验收。</div>
        </el-form-item>
        <el-form-item label="批次大小">
          <el-input-number
            v-model="form.batch_size"
            :min="1"
            :max="200"
            :step="10"
            controls-position="right"
          />
          <div class="field-help">每批独立提交，单批失败不会影响已完成批次。</div>
        </el-form-item>
        <div class="dialog-actions">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button native-type="submit" type="primary" :loading="submitting">开始导入</el-button>
        </div>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { createJamendoImport, listImportJobs } from '../../api/adminImports'
import PageHeader from '../../components/PageHeader.vue'
import StatePanel from '../../components/StatePanel.vue'
import type { ImportJobResponse, ImportJobStatus } from '../../types/importJob'
import { showError, showSuccess } from '../../utils/feedback'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
// 演示账号在后台只读：按钮直接禁用并说明原因，避免点下去才收到 403
const readonlyHint = '演示账号只能查看后台数据，不能修改'

const jobs = ref<ImportJobResponse[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const refreshTimer = ref<number | null>(null)
const form = reactive({ limit: 100, batch_size: 50 })

const activeStatuses: ReadonlySet<ImportJobStatus> = new Set(['pending', 'running'])
const statusTypes: Record<ImportJobStatus, 'info' | 'warning' | 'success' | 'danger'> = {
  pending: 'info',
  running: 'warning',
  completed: 'success',
  failed: 'danger',
}

// 拉取最近导入任务，并根据任务状态同步轮询定时器。
async function loadJobs(): Promise<void> {
  loading.value = true
  try {
    const { data } = await listImportJobs()
    jobs.value = data
  } catch (error) {
    showError(error, '导入任务加载失败')
  } finally {
    loading.value = false
    syncPolling()
  }
}

// 校验导入参数并创建后台任务，任务进度由轮询更新。
async function createJob(): Promise<void> {
  submitting.value = true
  try {
    await createJamendoImport({ limit: form.limit, batch_size: form.batch_size })
    showSuccess('导入任务已创建')
    dialogVisible.value = false
    await loadJobs()
  } catch (error) {
    showError(error, '导入任务创建失败')
  } finally {
    submitting.value = false
  }
}

// 仅在存在运行中任务时轮询，避免空闲页面持续请求。
function syncPolling(): void {
  const hasActiveJob = jobs.value.some((job) => activeStatuses.has(job.status))
  if (hasActiveJob && refreshTimer.value === null) {
    refreshTimer.value = window.setInterval(loadJobs, 3000)
  } else if (!hasActiveJob && refreshTimer.value !== null) {
    window.clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
}

// 将已处理数量换算为 Element Plus 进度条百分比。
function progress(job: ImportJobResponse): number {
  if (job.status === 'completed') return 100
  if (job.requested_limit <= 0) return 0
  return Math.min(99, Math.round((job.fetched / job.requested_limit) * 100))
}

// 将后端状态码转换为用户可读中文。
function statusLabel(status: ImportJobStatus): string {
  return { pending: '等待中', running: '执行中', completed: '已完成', failed: '失败' }[status]
}

// 为不同任务状态选择一致的视觉语义。
function statusTagType(status: ImportJobStatus): 'info' | 'warning' | 'success' | 'danger' {
  return statusTypes[status]
}

// 将 ISO 时间转换为本地化展示文本。
function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

// 合并失败原因统计，减少表格中的重复信息。
function failureSummary(job: ImportJobResponse): string {
  return Object.entries(job.failure_reasons)
    .map(([reason, count]) => `${reason}（${count}）`)
    .join('、')
}

onMounted(loadJobs)
onBeforeUnmount(() => {
  if (refreshTimer.value !== null) window.clearInterval(refreshTimer.value)
})
</script>

<style scoped>
.admin-imports-page {
  padding: var(--page-gutter);
}
.notice-card {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 24px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(41, 55, 77, 0.76), rgba(27, 34, 55, 0.7));
}
.notice-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 10px;
  color: var(--accent-strong);
  background: var(--accent-soft);
  font-size: 18px;
}
.notice-card strong {
  color: var(--text);
  font-size: 14px;
}
.notice-card p,
.muted,
.field-help {
  color: var(--text-muted);
  font-size: 12px;
}
.notice-card p {
  margin: 4px 0 0;
  line-height: 1.6;
}
.jobs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: rgba(39, 56, 85, 0.72);
  --el-table-row-hover-bg-color: rgba(50, 69, 102, 0.82);
  --el-table-header-bg-color: rgba(29, 42, 65, 0.88);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text-secondary);
  --el-table-header-text-color: var(--text-muted);
  border-radius: 14px;
  overflow: hidden;
}
.job-name {
  color: var(--text);
  font-weight: 650;
}
.result-count {
  display: block;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.65;
}
.error-text {
  color: var(--danger);
  font-size: 12px;
  line-height: 1.5;
}
.field-help {
  margin-top: 6px;
  line-height: 1.5;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 26px;
}
@media (max-width: 760px) {
  .admin-imports-page {
    padding: 24px 16px;
  }
}
</style>
