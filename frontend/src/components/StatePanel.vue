<!-- 统一加载、空数据和错误状态，保证反馈文案与操作入口一致。 -->
<template>
  <div class="state-panel" :class="`state-${type}`" role="status">
    <span v-if="type === 'loading'" class="spinner" aria-hidden="true"></span>
    <AppIcon v-else :name="icon" :size="22" class="icon" />
    <strong>{{ title }}</strong>
    <p v-if="message">{{ message }}</p>
    <div v-if="$slots.action" class="action"><slot name="action" /></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = withDefaults(
  defineProps<{ type?: 'loading' | 'empty' | 'error'; title: string; message?: string }>(),
  { type: 'empty' },
)
const icon = computed(() => ({ loading: 'info', empty: 'music', error: 'alert' })[props.type])
</script>

<style scoped>
.state-panel {
  position: relative;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8px;
  padding: 36px 20px;
  color: var(--text-secondary);
  text-align: center;
}
.icon {
  margin-bottom: 4px;
  color: var(--text-muted);
}
.state-error .icon {
  color: var(--danger);
}
.state-panel strong {
  color: var(--text);
  font-size: var(--fs-md);
  font-weight: 600;
}
.state-panel p {
  max-width: 380px;
  margin: 0;
  color: var(--text-muted);
  font-size: var(--fs-sm);
  line-height: 1.7;
}
.spinner {
  width: 18px;
  height: 18px;
  margin-bottom: 6px;
  border: 1.5px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}
.action {
  margin-top: 8px;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
