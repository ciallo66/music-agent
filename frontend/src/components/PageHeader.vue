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
  margin-bottom: 30px;
}
.heading-copy {
  min-width: 0;
}
.page-header h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(26px, 3vw, 36px);
  line-height: 1.12;
  letter-spacing: -0.04em;
}
.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.subtitle {
  max-width: 660px;
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.65;
}
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
@media (max-width: 640px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
    margin-bottom: 24px;
  }
  .actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
