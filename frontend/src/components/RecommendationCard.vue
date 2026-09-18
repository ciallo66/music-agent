<!-- 结构化推荐结果卡片：展示推荐理由、标签、适用场景和可执行操作。 -->
<template>
  <article class="recommendation-card page-surface">
    <header class="card-header">
      <div>
        <p class="card-eyebrow">为你推荐</p>
        <h3>{{ card.title }}</h3>
      </div>
      <div class="card-tags" v-if="card.tags && card.tags.length">
        <span v-for="tag in card.tags" :key="tag" class="card-tag">{{ tag }}</span>
      </div>
    </header>

    <p class="card-reason">{{ card.reason }}</p>
    <div v-if="card.scenario" class="card-scenario">
      <span class="scenario-icon">🎯</span>
      <span>适用场景：{{ card.scenario }}</span>
    </div>

    <ul class="card-tracklist">
      <li v-for="(item, index) in card.items" :key="item.id" class="track-row">
        <router-link :to="`/songs/${item.id}`" class="track-link">
          <span class="track-number">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="track-meta">
            <strong>{{ item.title }}</strong>
            <small>{{ item.artist.name }} · {{ item.genre || '未知风格' }}</small>
          </div>
          <div class="track-meta-right">
            <span class="track-score" v-if="item.match_score !== null"
              >{{ Math.round(item.match_score * 100) }}%</span
            >
            <span class="track-reason-mini">{{ item.reason }}</span>
          </div>
        </router-link>
        <div class="feature-list" aria-label="内容特征">
          <span v-if="item.bpm">节奏 {{ Math.round(item.bpm) }} BPM</span>
          <span v-if="item.energy !== null">能量 {{ formatPercent(item.energy) }}</span>
          <span v-if="item.valence !== null">情绪明亮度 {{ formatPercent(item.valence) }}</span>
          <span v-if="item.danceability !== null" :title="danceabilityHint(item.danceability)"
            >律动 {{ danceabilityLabel(item.danceability) }}</span
          >
        </div>
        <div class="track-actions">
          <button
            v-for="action in feedbackActions"
            :key="action.action"
            type="button"
            class="track-action"
            :class="`track-action-${action.action}`"
            :title="action.label"
            @click="onFeedback(item.id, action.action)"
          >
            {{ action.action === 'like' ? '喜欢' : '不合适' }}
          </button>
          <router-link class="detail-link" :to="`/songs/${item.id}`">查看分析</router-link>
          <el-button size="small" type="primary" @click="onAddToCollection(item.id)"
            >加入集合</el-button
          >
        </div>
      </li>
    </ul>

    <footer class="card-footer">
      <el-button size="small" @click="$emit('refresh')">换一批</el-button>
      <el-button
        size="small"
        type="primary"
        @click="$emit('openAgent', { type: 'recommendation', query: card.title })"
        >在智能体中继续</el-button
      >
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StructuredRecommendationCard, FeedbackActionItem } from '../types/music'
import { danceabilityHint, danceabilityLabel } from '../types/music'
import { useFeedbackStore } from '../stores/feedback'

const props = defineProps<{
  card: StructuredRecommendationCard
  actions: FeedbackActionItem[]
}>()

const emit = defineEmits<{
  refresh: []
  feedback: [payload: { songId: number; action: string }]
  openAgent: [payload: { type: string; query: string }]
}>()

const feedbackStore = useFeedbackStore()

const feedbackActions = computed(() =>
  props.actions.filter((action) => action.action === 'like' || action.action === 'dislike'),
)

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

function isSubmitting(songId: number): boolean {
  return feedbackStore.submitted.has(songId)
}

async function onFeedback(songId: number, action: string) {
  if (isSubmitting(songId)) return
  await feedbackStore.submitFeedback(songId, action)
  emit('feedback', { songId, action })
}

function onAddToCollection(songId: number) {
  emit('openAgent', { type: 'add-to-collection', query: `将歌曲ID ${songId} 加入集合` })
}
</script>

<style scoped>
.recommendation-card {
  padding: 22px;
  margin-bottom: 22px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.card-eyebrow {
  margin: 0;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.card-header h3 {
  margin: 6px 0 0;
  font-size: 18px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.card-tag {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--accent-strong);
  font-size: 11px;
}

.card-reason {
  margin: 0 0 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.card-scenario {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-secondary);
  font-size: 12px;
  background: rgba(110, 231, 210, 0.06);
}

.card-tracklist {
  list-style: none;
  margin: 18px 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.track-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(17, 28, 47, 0.48);
}

.track-link {
  display: flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.track-number {
  width: 34px;
  color: var(--text-muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.track-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.track-meta strong {
  font-size: 13px;
  color: var(--text);
}

.track-meta small {
  color: var(--text-muted);
  font-size: 11px;
}

.track-meta-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.track-score {
  color: var(--accent-strong);
  font-size: 12px;
  font-weight: 600;
}

.track-reason-mini {
  color: var(--text-muted);
  font-size: 11px;
}

.track-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-left: 46px;
}

.feature-list span {
  padding: 4px 8px;
  border-radius: 7px;
  color: var(--text-secondary);
  background: rgba(110, 231, 210, 0.08);
  font-size: 10px;
}

.track-action {
  height: 32px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}

.detail-link {
  display: inline-flex;
  height: 32px;
  align-items: center;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  text-decoration: none;
}

.detail-link:hover {
  border-color: var(--border-strong);
  color: var(--text);
}

.track-action:hover {
  background: var(--surface-hover);
}

.track-action-like:hover {
  border-color: var(--accent);
  color: var(--accent-strong);
}

.track-action-dislike:hover {
  border-color: var(--danger);
  color: var(--danger);
}

.track-action-seen:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.track-action-similar:hover {
  border-color: var(--accent-purple);
  color: var(--accent-purple);
}

.track-action-less:hover {
  border-color: var(--warning);
  color: var(--warning);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

@media (max-width: 640px) {
  .card-header {
    flex-direction: column;
  }

  .track-meta-right {
    display: none;
  }

  .card-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
