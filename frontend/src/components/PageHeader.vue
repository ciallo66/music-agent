<template>
  <header class="page-header">
    <div>
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
  margin-bottom: 28px;
}
.page-header h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(24px, 3vw, 32px);
  letter-spacing: -0.04em;
}
.eyebrow {
  margin: 0 0 8px;
  color: var(--accent-strong);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.subtitle {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 14px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
@media (max-width: 640px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
