<!-- 结构化推荐结果：一块标题 + 理由 + 一组内容行。
     不再用「卡片里再套卡片」，行与行之间靠分隔线区分。 -->
<template>
  <article class="recommendation">
    <header class="rec-header">
      <div class="rec-heading">
        <h3>{{ card.title }}</h3>
        <p v-if="card.tags.length" class="rec-tags">{{ card.tags.join(' · ') }}</p>
      </div>
    </header>

    <p class="rec-reason">{{ card.reason }}</p>
    <p v-if="card.scenario" class="rec-scenario">适用场景：{{ card.scenario }}</p>

    <ul class="rec-list">
      <li v-for="item in card.items" :key="item.id" class="rec-row">
        <div class="rec-main">
          <router-link class="rec-link" :to="`/songs/${item.id}`">
            <SongCover :song="item" size="sm" />
            <span class="rec-copy">
              <strong>{{ item.title }}</strong>
              <small>{{ item.artist.name }} · {{ item.genre || '未知风格' }}</small>
            </span>
            <span v-if="item.match_score !== null" class="rec-score numeric">
              {{ Math.round(item.match_score * 100) }}<i>%</i>
            </span>
          </router-link>
          <p class="rec-item-reason">{{ item.reason }}</p>
          <p class="rec-features">
            <span v-if="item.bpm">{{ Math.round(item.bpm) }} BPM</span>
            <span v-if="item.energy !== null">能量 {{ formatPercent(item.energy) }}</span>
            <span v-if="item.valence !== null">明亮度 {{ formatPercent(item.valence) }}</span>
            <span v-if="item.danceability !== null" :title="danceabilityHint(item.danceability)"
              >律动 {{ danceabilityLabel(item.danceability) }}</span
            >
          </p>
        </div>
        <div class="rec-actions">
          <button
            v-for="action in feedbackActions"
            :key="action.action"
            type="button"
            class="text-button"
            :class="{ 'is-active': feedbackStore.mine[item.id] === action.action }"
            :title="action.label"
            :aria-pressed="feedbackStore.mine[item.id] === action.action"
            @click="onFeedback(item.id, action.action)"
          >
            {{ action.label }}
          </button>
          <router-link class="text-button" :to="`/songs/${item.id}`">查看分析</router-link>
          <button type="button" class="text-button" @click="onAddToCollection(item.id)">
            加入集合
          </button>
        </div>
      </li>
    </ul>

    <footer class="rec-footer">
      <span>匹配度来自内容特征与你的历史反馈，不是随机结果。</span>
      <button
        type="button"
        class="text-button text-button--accent"
        @click="$emit('openAgent', { type: 'recommendation', query: card.title })"
      >
        在智能体中继续
      </button>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StructuredRecommendationCard, FeedbackActionItem } from '../types/music'
import { danceabilityHint, danceabilityLabel } from '../types/music'
import SongCover from './SongCover.vue'
import { useFeedbackStore } from '../stores/feedback'

const props = defineProps<{
  card: StructuredRecommendationCard
  actions: FeedbackActionItem[]
}>()

const emit = defineEmits<{
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
.recommendation {
  padding-top: 2px;
}

.rec-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.rec-heading h3 {
  margin: 0;
  color: var(--text);
  font-size: var(--fs-md);
  font-weight: 600;
}

.rec-tags {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.text-button {
  flex: 0 0 auto;
  padding: 0;
  border: 0;
  color: var(--text-muted);
  background: transparent;
  font-family: inherit;
  font-size: var(--fs-xs);
  cursor: pointer;
}

.text-button:hover {
  color: var(--text);
}

.text-button--accent:hover {
  color: var(--accent-strong);
}

/* 已提交的反馈保持高亮，用户不用回忆自己点过什么 */
.text-button.is-active {
  color: var(--accent-strong);
}

.rec-reason {
  max-width: 760px;
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.rec-scenario {
  margin: 6px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.rec-list {
  margin: 14px 0 0;
  padding: 0;
  border-top: 1px solid var(--border);
  list-style: none;
}

.rec-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.rec-main {
  min-width: 0;
  flex: 1;
}

.rec-link {
  display: flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  text-decoration: none;
}

.rec-copy {
  min-width: 0;
  flex: 1;
}

.rec-copy strong,
.rec-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rec-copy strong {
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 500;
}

.rec-copy small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.rec-score {
  margin-left: 4px;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}

.rec-score i {
  color: var(--text-muted);
  font-style: normal;
  font-size: 11px;
}

.rec-item-reason {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.rec-features {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  margin: 6px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.rec-actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 2px;
}

.rec-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

@media (max-width: 760px) {
  .rec-row {
    flex-direction: column;
    gap: 8px;
  }

  .rec-actions {
    justify-content: flex-start;
    gap: 16px;
  }

  /* 触屏上文字按钮也要有 32px 的点击高度 */
  .rec-actions .text-button {
    display: inline-flex;
    min-height: 32px;
    align-items: center;
  }

  .rec-footer span {
    display: none;
  }
}
</style>
