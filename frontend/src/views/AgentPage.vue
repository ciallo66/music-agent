<template>
  <section class="agent-page">
    <PageHeader title="AI 音乐助手" subtitle="用你的播放和收藏记录，获得可解释的音乐建议" />
    <div class="conversation" aria-live="polite">
      <div v-for="(item, index) in messages" :key="index" class="message" :class="item.role">
        <span class="role-label">{{ item.role === 'user' ? '你' : '助手' }}</span>
        <p>{{ item.content }}</p>
      </div>
      <StatePanel v-if="loading" type="loading" title="正在分析" message="请稍候…" />
      <p v-if="toolStatus" class="tool-status">● {{ toolStatus }}</p>
    </div>
    <form class="composer" @submit.prevent="sendMessage">
      <el-input
        v-model="draft"
        maxlength="2000"
        show-word-limit
        placeholder="例如：分析我的音乐偏好"
        :disabled="loading"
      />
      <el-button
        type="primary"
        native-type="submit"
        :loading="loading"
        :disabled="draft.trim().length === 0"
        >发送</el-button
      >
    </form>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import { streamAgentChat, type AgentEvent } from '../api/agent'
import { showError } from '../utils/feedback'

interface Message {
  role: 'user' | 'assistant'
  content: string
}
const draft = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])
const sessionId = ref<number | null>(null)
const toolStatus = ref('')

async function sendMessage(): Promise<void> {
  const message = draft.value.trim()
  if (!message || loading.value) return
  messages.value.push({ role: 'user', content: message })
  draft.value = ''
  loading.value = true
  let assistantIndex: number | null = null
  try {
    const returnedSessionId = await streamAgentChat({
      message,
      sessionId: sessionId.value,
      onEvent: (event: AgentEvent) => {
        if (event.type === 'tool') toolStatus.value = event.content
        if (event.type === 'tool_error') toolStatus.value = `工具调用失败：${event.content}`
        if (event.type === 'error') throw new Error(event.content)
        if (event.type !== 'content' && event.type !== 'content_delta') return
        if (assistantIndex === null) {
          assistantIndex = messages.value.push({ role: 'assistant', content: '' }) - 1
        }
        if (event.type === 'content') {
          if (messages.value[assistantIndex].content.length === 0) {
            messages.value[assistantIndex].content = event.content
          }
        } else {
          messages.value[assistantIndex].content += event.content
        }
      },
    })
    if (returnedSessionId !== null) sessionId.value = returnedSessionId
    if (assistantIndex === null)
      messages.value.push({ role: 'assistant', content: '暂时没有分析结果。' })
  } catch {
    showError('助手暂时不可用，请稍后重试')
  } finally {
    loading.value = false
    toolStatus.value = ''
  }
}
</script>

<style scoped>
.agent-page {
  max-width: 900px;
  padding: 40px;
}
.conversation {
  min-height: 360px;
  padding: 24px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--surface);
}
.message {
  max-width: 80%;
  margin-bottom: 18px;
  padding: 14px 16px;
  border-radius: 14px;
  color: var(--text);
}
.message.user {
  margin-left: auto;
  background: var(--accent-soft);
}
.message.assistant {
  background: var(--surface-raised);
}
.role-label {
  color: var(--accent-strong);
  font-size: 12px;
  font-weight: 700;
}
.message p {
  margin: 6px 0 0;
  line-height: 1.6;
}
.composer {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}
.tool-status {
  margin: 12px 0 0;
  color: var(--accent-strong);
  font-size: 13px;
}
@media (max-width: 640px) {
  .agent-page {
    padding: 24px 16px;
  }
  .composer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
