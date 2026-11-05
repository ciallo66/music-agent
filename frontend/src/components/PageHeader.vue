<!-- 统一页面标题、说明和右侧操作区，避免页面重复实现头部布局。 -->
<template>
  <header class="page-header">
    <div class="heading-copy">
      <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
      <h2>{{ title }}</h2>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="actions"><slot name="actions" /></div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string; subtitle?: string; eyebrow?: string }>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}
.heading-copy {
  min-width: 0;
}
.page-header h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(22px, 2.4vw, 28px);
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.01em;
}
.eyebrow {
  margin: 0 0 6px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  font-weight: 500;
}
.subtitle {
  max-width: 680px;
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.7;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
@media (max-width: 640px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
    margin-bottom: 20px;
  }
  .actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
