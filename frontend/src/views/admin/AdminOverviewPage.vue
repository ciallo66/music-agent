<!-- 管理后台概览：库表计数 + 流派分布，用于一眼看出数据是否健康。 -->
<template>
  <section class="admin-page">
    <PageHeader title="概览" subtitle="曲库、账号与互动数据的整体情况">
      <template #actions>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </template>
    </PageHeader>

    <StatePanel v-if="loading && overview === null" type="loading" title="正在读取统计数据" />
    <StatePanel
      v-else-if="overview === null"
      type="error"
      title="统计数据读取失败"
      :message="errorMessage"
    >
      <template #action>
        <button class="retry-button" type="button" @click="load">重新加载</button>
      </template>
    </StatePanel>

    <template v-else>
      <div class="metric-grid">
        <article v-for="item in metrics" :key="item.label" class="metric-card">
          <p>{{ item.label }}</p>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </article>
      </div>

      <div class="panel-grid">
        <article class="panel">
          <h3>流派分布</h3>
          <ul class="dist-list">
            <li v-for="item in overview.genre_distribution" :key="item.label">
              <span>{{ item.label }}</span>
              <div class="dist-track">
                <span :style="{ width: `${percent(item.count)}%` }"></span>
              </div>
              <strong>{{ item.count }}</strong>
            </li>
          </ul>
          <p v-if="!overview.genre_distribution.length" class="muted">暂无流派数据。</p>
        </article>

        <article class="panel">
          <h3>数据完整度</h3>
          <ul class="health-list">
            <li>
              <span>已生成向量</span>
              <strong>{{ overview.songs_with_embedding }} / {{ overview.songs }}</strong>
            </li>
            <li>
              <span>含音频特征</span>
              <strong>{{ overview.songs_with_audio_features }} / {{ overview.songs }}</strong>
            </li>
            <li>
              <span>知识库切片</span>
              <strong>{{ overview.knowledge }}</strong>
            </li>
            <li>
              <span>导入任务</span>
              <strong>{{ overview.import_jobs }}</strong>
            </li>
          </ul>
          <p class="muted">
            说明：本平台不托管音频，「收听次数」只有在接入可播放音源后才会增长；当前推荐依据收藏与主动反馈。
          </p>
        </article>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../../components/PageHeader.vue'
import StatePanel from '../../components/StatePanel.vue'
import { getAdminOverview, type AdminOverview } from '../../api/admin'
import { showError } from '../../utils/feedback'

const overview = ref<AdminOverview | null>(null)
const loading = ref(false)
const errorMessage = ref('')

const metrics = computed(() => {
  const data = overview.value
  if (data === null) return []
  return [
    { label: '曲目', value: data.songs, hint: `${data.artists} 位歌手` },
    { label: '账号', value: data.users, hint: `${data.admins} 位管理员` },
    { label: '歌单', value: data.playlists, hint: '用户创建' },
    { label: '收藏', value: data.favorites, hint: '用户收藏总量' },
    { label: '主动反馈', value: data.feedback, hint: '喜欢/不感兴趣等' },
    { label: '收听记录', value: data.plays, hint: '需可播放音源' },
  ]
})

// 分布条宽度按最大值缩放，避免最长的一条总是占满。
const percent = (count: number): number => {
  const max = Math.max(...(overview.value?.genre_distribution ?? []).map((item) => item.count), 1)
  return Math.round((count / max) * 100)
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await getAdminOverview()
    overview.value = data
  } catch (error) {
    errorMessage.value = '暂时无法读取统计，请稍后重试。'
    showError(error, '后台统计加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.metric-card {
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
}
.metric-card p {
  margin: 0;
  color: var(--text-muted);
  font-size: 11px;
}
.metric-card strong {
  display: block;
  margin: 6px 0 2px;
  color: var(--text);
  font-size: 22px;
}
.metric-card small {
  color: var(--text-muted);
  font-size: 10px;
}
.panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}
.panel {
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
}
.panel h3 {
  margin: 0 0 12px;
  color: var(--text);
  font-size: 13px;
}
.dist-list,
.health-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.dist-list li {
  display: grid;
  grid-template-columns: 72px 1fr 44px;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 12px;
}
.dist-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.dist-track span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
}
.dist-list strong {
  color: var(--text);
  text-align: right;
}
.health-list li {
  display: flex;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 12px;
}
.health-list strong {
  color: var(--text);
}
.muted {
  margin: 12px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.7;
}
.retry-button {
  padding: 6px 12px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  color: var(--text);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
}
</style>
