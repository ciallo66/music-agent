<template>
  <div class="state-panel" :class="`state-${type}`" role="status">
    <span v-if="type === 'loading'" class="spinner" aria-hidden="true"></span>
    <span class="icon" aria-hidden="true">{{ icon }}</span>
    <strong>{{ title }}</strong>
    <p v-if="message">{{ message }}</p>
    <div v-if="$slots.action" class="action"><slot name="action" /></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(
  defineProps<{ type?: 'loading' | 'empty' | 'error'; title: string; message?: string }>(),
  { type: 'empty' },
)
const icon = computed(() => ({ loading: '◌', empty: '♪', error: '!' })[props.type])
</script>

<style scoped>
.state-panel {
  position: relative;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 11px;
  padding: 38px 20px;
  color: var(--text-secondary);
  text-align: center;
}
.icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: 16px;
  color: var(--accent-strong);
  background: var(--accent-soft);
  font-size: 23px;
  box-shadow: 0 12px 30px rgba(22, 186, 165, 0.11);
}
.state-panel strong {
  color: var(--text);
  font-size: 16px;
}
.state-panel p {
  max-width: 340px;
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}
.spinner {
  position: absolute;
  width: 42px;
  height: 42px;
  border: 2px solid transparent;
  border-top-color: var(--accent-strong);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.action {
  margin-top: 6px;
}
.state-loading .icon {
  opacity: 0;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
