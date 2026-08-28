<template>
  <div class="state-panel" :class="`state-${type}`" role="status">
    <span v-if="type === 'loading'" class="spinner" aria-hidden="true"></span>
    <span class="icon" aria-hidden="true">{{ icon }}</span>
    <strong>{{ title }}</strong>
    <p v-if="message">{{ message }}</p>
    <el-button v-if="$slots.action" text type="primary"><slot name="action" /></el-button>
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
  gap: 10px;
  color: var(--text-secondary);
  text-align: center;
}
.icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: 14px;
  color: var(--accent-strong);
  background: var(--accent-soft);
  font-size: 22px;
}
.state-panel strong {
  color: var(--text);
  font-size: 15px;
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
.state-loading .icon {
  opacity: 0;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
