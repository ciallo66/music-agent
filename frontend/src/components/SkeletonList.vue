<!-- 列表加载骨架：在数据返回前占位，避免加载完成时内容跳动。
     内置 role="status" 播报，保证屏幕阅读器仍能感知加载中状态。 -->
<template>
  <div class="skeleton-wrap">
    <p class="skeleton-status" role="status">{{ status }}</p>
    <div class="skeleton" :class="`skeleton-${variant}`" aria-hidden="true">
      <div v-for="row in rows" :key="row" class="skeleton-row">
        <span class="skeleton-shape skeleton-thumb" />
        <span class="skeleton-lines">
          <span class="skeleton-shape skeleton-line is-title" />
          <span class="skeleton-shape skeleton-line is-meta" />
        </span>
        <span class="skeleton-shape skeleton-tail" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 占位行数 */
    rows?: number
    /** 布局变体：song 为横向列表行，card 为卡片网格 */
    variant?: 'song' | 'card'
    /** 供屏幕阅读器播报的加载提示 */
    status?: string
  }>(),
  { rows: 6, variant: 'song', status: '正在加载内容' },
)
</script>

<style scoped>
/* 视觉隐藏但保留给辅助技术读取 */
.skeleton-status {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-card {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
}

.skeleton-card .skeleton-row {
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
  padding: 16px;
}

.skeleton-shape {
  display: block;
  border-radius: 8px;
  /* 静态底色兜底，用户声明减少动效时也能看出是占位 */
  background: rgba(255, 255, 255, 0.07);
}

/* 仅在用户未声明减少动效时播放微光 */
@media (prefers-reduced-motion: no-preference) {
  .skeleton-shape {
    background-image: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.04) 0%,
      rgba(255, 255, 255, 0.12) 50%,
      rgba(255, 255, 255, 0.04) 100%
    );
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.4s ease-in-out infinite;
  }
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }

  100% {
    background-position: -200% 0;
  }
}

.skeleton-thumb {
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  border-radius: 12px;
}

.skeleton-card .skeleton-thumb {
  width: 100%;
  height: 84px;
}

.skeleton-lines {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 11px;
}

.skeleton-line.is-title {
  width: 46%;
}

.skeleton-line.is-meta {
  width: 26%;
  height: 9px;
}

.skeleton-tail {
  width: 52px;
  height: 11px;
  flex-shrink: 0;
}

.skeleton-card .skeleton-tail {
  display: none;
}

@media (max-width: 640px) {
  .skeleton-tail {
    display: none;
  }

  .skeleton-line.is-title {
    width: 68%;
  }
}
</style>
