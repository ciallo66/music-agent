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
  gap: 6px;
}

/* 加载占位与真实列表占用相近的高度：
   以前这里是固定行数（内容库 8 行 ≈ 896px），而真实内容区只有 300~500px 高，
   数据到达时整页会塌下来一大截 —— 用户看到的就是「跳转时闪一下」。 */
.skeleton-wrap {
  min-height: var(--content-min-height, 420px);
}

.skeleton-card {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.skeleton-card .skeleton-row {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  padding: 14px;
}

.skeleton-shape {
  display: block;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.06);
}

/* 用呼吸式明暗代替流光扫过：更安静，也不会让人觉得页面在“加载动画表演” */
@media (prefers-reduced-motion: no-preference) {
  .skeleton-shape {
    animation: skeleton-pulse 1.8s ease-in-out infinite;
  }
}

@keyframes skeleton-pulse {
  0%,
  100% {
    opacity: 0.55;
  }

  50% {
    opacity: 1;
  }
}

.skeleton-thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}

.skeleton-card .skeleton-thumb {
  width: 100%;
  height: 78px;
}

.skeleton-lines {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 10px;
}

.skeleton-line.is-title {
  width: 42%;
}

.skeleton-line.is-meta {
  width: 24%;
  height: 8px;
}

.skeleton-tail {
  width: 44px;
  height: 10px;
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
    width: 64%;
  }
}
</style>
