<!-- Agent 对话页面：展示流式回复、工具状态和可复用的提问入口。 -->
<template>
  <section class="agent-page">
    <PageHeader
      eyebrow="AI AGENT WORKSPACE"
      title="AI 智能体"
      subtitle="调用音乐数据工具，完成检索、分析和可解释的知识问答"
    >
      <template #actions
        ><el-button v-if="messages.length" :disabled="loading" @click="startNewConversation"
          >＋ 新对话</el-button
        ></template
      >
    </PageHeader>

    <div ref="conversationElement" class="conversation page-surface" aria-live="polite">
      <div v-if="messages.length === 0" class="welcome-state">
        <div class="assistant-mark" aria-hidden="true"><span>✦</span><i></i></div>
        <p>AI AGENT</p>
        <h2>今天想让智能体处理什么？</h2>
        <span>我可以调用已接入的数据工具，检索资料、分析偏好并说明判断依据。</span>
        <div class="prompt-grid">
          <button
            v-for="prompt in starterPrompts"
            :key="prompt.title"
            type="button"
            @click="useStarterPrompt(prompt.message)"
          >
            <span aria-hidden="true">{{ prompt.icon }}</span>
            <strong>{{ prompt.title }}</strong>
            <small>{{ prompt.description }}</small>
            <i aria-hidden="true">→</i>
          </button>
        </div>
      </div>

      <template v-else>
        <div v-for="(item, index) in messages" :key="index" class="message-row" :class="item.role">
          <span class="message-avatar" aria-hidden="true">{{
            item.role === 'user' ? userInitial : '✦'
          }}</span>
          <div class="message">
            <span class="role-label">{{ item.role === 'user' ? '你' : 'AI 智能体' }}</span>
            <p>{{ item.content }}</p>
          </div>
        </div>
        <div v-if="loading && !hasPendingAssistant" class="message-row assistant pending">
          <span class="message-avatar" aria-hidden="true">✦</span>
          <div class="message">
            <span class="role-label">AI 智能体</span>
            <p class="typing"><i></i><i></i><i></i></p>
          </div>
        </div>
        <p v-if="toolStatus" class="tool-status"><span></span>{{ toolStatus }}</p>
      </template>
    </div>

    <div v-if="awaitingConfirmation" class="confirmation-panel page-surface">
      <div class="confirmation-head">
        <span class="confirmation-badge">需要确认</span>
        <div>
          <strong>以下操作会修改数据，确认后才会执行</strong>
          <small>执行前你可以拒绝，智能体会改用其它方式回答</small>
        </div>
      </div>
      <ul class="confirmation-list">
        <li v-for="item in pendingConfirmations" :key="item.confirmationId">
          <span class="op-tag">{{ operationLabel(item.operation) }}</span>
          <div class="confirmation-detail">
            <strong>{{ item.name }}</strong>
            <small v-if="item.reason">{{ item.reason }}</small>
            <code>{{ formatArguments(item.arguments) }}</code>
          </div>
        </li>
      </ul>
      <div class="confirmation-actions">
        <el-button :disabled="loading" @click="respondToConfirmations(false)">拒绝</el-button>
        <el-button type="primary" :loading="loading" @click="respondToConfirmations(true)">
          确认执行
        </el-button>
      </div>
    </div>

    <form class="composer page-surface" @submit.prevent="sendMessage">
      <el-input
        v-model="draft"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 5 }"
        maxlength="2000"
        resize="none"
        placeholder="输入问题，例如：根据我的偏好推荐几首歌…"
        :disabled="loading || awaitingConfirmation"
        @keydown="handleComposerKeydown"
      />
      <div class="composer-footer">
        <span>Enter 发送 · Shift + Enter 换行</span>
        <el-button
          native-type="submit"
          type="primary"
          :loading="loading"
          :disabled="draft.trim().length === 0 || awaitingConfirmation"
        >
          {{ loading ? '分析中' : '发送' }} <span v-if="!loading" aria-hidden="true">↗</span>
        </el-button>
      </div>
    </form>
    <p class="assistant-notice">AI 回答可能存在偏差，重要信息请结合歌曲详情与实际数据判断。</p>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import { parseToolConfirmation, streamAgentChat, streamToolConfirmations } from '../api/agent'
import type { AgentEvent, PendingToolConfirmation } from '../types/agent'
import { showError } from '../utils/feedback'
import { useAuthStore } from '../stores/auth'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const starterPrompts = [
  {
    icon: '◫',
    title: '分析音乐偏好',
    description: '总结我最近喜欢的风格',
    message: '分析我的音乐偏好，并说明判断依据。',
  },
  {
    icon: '♫',
    title: '发现新音乐',
    description: '按我的喜好推荐歌曲',
    message: '根据我的播放和收藏记录，推荐一些我可能喜欢的歌曲。',
  },
  {
    icon: '☾',
    title: '创建场景歌单',
    description: '为当下状态寻找音乐',
    message: '帮我挑选一些适合夜晚放松时听的歌曲。',
  },
  {
    icon: '⌁',
    title: '解释推荐原因',
    description: '看看推荐背后的依据',
    message: '解释平台会根据哪些信息为我推荐音乐。',
  },
]
const auth = useAuthStore()
const draft = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])
const sessionId = ref<number | null>(null)
const toolStatus = ref('')
const pendingConfirmations = ref<PendingToolConfirmation[]>([])
const conversationElement = ref<HTMLElement | null>(null)
const userInitial = computed(() => auth.user?.username.slice(0, 1).toUpperCase() || '你')
const hasPendingAssistant = computed(
  () => messages.value[messages.value.length - 1]?.role === 'assistant',
)
// 有未确认的高风险操作时，先让用户处理完再继续对话。
const awaitingConfirmation = computed(() => pendingConfirmations.value.length > 0)

// 流式回复期间滚动到底部，保证用户始终看到最新内容。
async function scrollToLatest(): Promise<void> {
  await nextTick()
  const element = conversationElement.value
  if (element !== null) element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
}

// 创建一次流式消费的事件处理器，内部维护当前助手消息的位置。
function createEventHandler(): {
  handle: (event: AgentEvent) => void
  ensureAssistantText: () => void
} {
  let assistantIndex: number | null = null
  const handle = (event: AgentEvent): void => {
    if (event.type === 'tool') toolStatus.value = event.content
    if (event.type === 'tool_error') toolStatus.value = `工具调用失败：${event.content}`
    if (event.type === 'tool_rejected') toolStatus.value = '已按你的选择拒绝该操作'
    if (event.type === 'confirmation_required') {
      const pending = parseToolConfirmation(event.content)
      if (pending !== null) {
        pendingConfirmations.value.push(pending)
        toolStatus.value = '有高风险操作等待你确认'
      }
      return
    }
    if (event.type === 'error') throw new Error(event.content)
    if (event.type !== 'content' && event.type !== 'content_delta') return
    if (assistantIndex === null)
      assistantIndex = messages.value.push({ role: 'assistant', content: '' }) - 1
    const assistantMessage = messages.value[assistantIndex]
    if (event.type === 'content') {
      if (assistantMessage.content.length === 0) assistantMessage.content = event.content
    } else {
      assistantMessage.content += event.content
    }
    void scrollToLatest()
  }
  const ensureAssistantText = (): void => {
    if (assistantIndex === null)
      messages.value.push({ role: 'assistant', content: '暂时没有分析结果，请换一种方式提问。' })
  }
  return { handle, ensureAssistantText }
}

// 消费一段 Agent 流，统一处理加载状态、会话 ID 和错误提示。
async function consumeStream(
  run: (onEvent: (event: AgentEvent) => void) => Promise<number | null>,
  failureHint: string,
): Promise<void> {
  loading.value = true
  toolStatus.value = ''
  const { handle, ensureAssistantText } = createEventHandler()
  await scrollToLatest()
  try {
    const returnedSessionId = await run(handle)
    if (returnedSessionId !== null) sessionId.value = returnedSessionId
    ensureAssistantText()
  } catch (error) {
    showError(error, failureHint)
  } finally {
    loading.value = false
    toolStatus.value = ''
    await scrollToLatest()
  }
}

// 发送消息并消费 SSE；文本增量直接更新最后一条助手消息。
async function sendMessage(): Promise<void> {
  const message = draft.value.trim()
  if (!message || loading.value || awaitingConfirmation.value) return
  messages.value.push({ role: 'user', content: message })
  draft.value = ''
  await consumeStream(
    (onEvent) => streamAgentChat({ message, sessionId: sessionId.value, onEvent }),
    '助手暂时不可用，请稍后重试',
  )
}

// 提交用户对高风险操作的决定，并继续消费同一条 Agent 流。
async function respondToConfirmations(approved: boolean): Promise<void> {
  const currentSessionId = sessionId.value
  if (currentSessionId === null || loading.value || !awaitingConfirmation.value) return
  const decisions = pendingConfirmations.value.map((item) => ({
    confirmationId: item.confirmationId,
    approved,
  }))
  pendingConfirmations.value = []
  messages.value.push({ role: 'user', content: approved ? '确认执行该操作' : '拒绝该操作' })
  await consumeStream(
    (onEvent) => streamToolConfirmations({ sessionId: currentSessionId, decisions, onEvent }),
    '确认操作失败，请重试',
  )
}

// 展示操作类型的中文标签。
function operationLabel(operation: string): string {
  if (operation === 'delete') return '删除'
  if (operation === 'write') return '写入'
  return '操作'
}

// 待确认参数只用于展示，截断过长内容避免撑破面板。
function formatArguments(args: Record<string, unknown>): string {
  const text = JSON.stringify(args)
  return text.length > 160 ? `${text.slice(0, 160)}…` : text
}

// 将快捷提问交给同一发送流程，保持行为一致。
async function useStarterPrompt(message: string): Promise<void> {
  draft.value = message
  await sendMessage()
}

// 清空当前展示和会话 ID，下一次提问会创建新会话。
function startNewConversation(): void {
  messages.value = []
  sessionId.value = null
  toolStatus.value = ''
  draft.value = ''
  pendingConfirmations.value = []
}

// Enter 发送、Shift+Enter 换行；输入法组合期间不抢占回车。
function handleComposerKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void sendMessage()
}
</script>

<style scoped>
.agent-page {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: var(--page-gutter);
}
.conversation {
  min-height: 420px;
  max-height: calc(100vh - 310px);
  flex: 1;
  padding: clamp(18px, 3vw, 34px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
.welcome-state {
  display: flex;
  min-height: 350px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
}
.assistant-mark {
  position: relative;
  display: grid;
  width: 70px;
  height: 70px;
  place-items: center;
  margin-bottom: 20px;
  border: 1px solid rgba(110, 231, 210, 0.28);
  border-radius: 22px;
  color: var(--accent);
  background: linear-gradient(145deg, rgba(110, 231, 210, 0.17), rgba(169, 162, 255, 0.15));
  box-shadow: 0 20px 45px rgba(17, 180, 159, 0.13);
  font-size: 27px;
}
.assistant-mark i {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 11px;
  height: 11px;
  border: 2px solid var(--surface-solid);
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 15px var(--accent);
}
.welcome-state > p {
  margin: 0 0 9px;
  color: var(--accent);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.18em;
}
.welcome-state h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(23px, 3vw, 33px);
  letter-spacing: -0.04em;
}
.welcome-state > span {
  max-width: 620px;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.8;
}
.prompt-grid {
  display: grid;
  width: min(100%, 780px);
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 28px;
}
.prompt-grid button {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  grid-template-rows: auto auto;
  align-items: center;
  gap: 2px 10px;
  padding: 13px;
  border: 1px solid var(--border);
  border-radius: 13px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  text-align: left;
}
.prompt-grid button > span {
  display: grid;
  width: 34px;
  height: 34px;
  grid-row: 1 / 3;
  place-items: center;
  border-radius: 10px;
  color: var(--accent);
  background: var(--accent-soft);
}
.prompt-grid strong {
  font-size: 11px;
}
.prompt-grid small {
  color: var(--text-muted);
  font-size: 9px;
}
.prompt-grid i {
  grid-row: 1 / 3;
  grid-column: 3;
  color: var(--text-muted);
  font-style: normal;
}
.prompt-grid button:hover {
  border-color: rgba(110, 231, 210, 0.35);
  background: var(--accent-soft);
  transform: translateY(-2px);
}
.prompt-grid button:hover i {
  color: var(--accent);
  transform: translateX(2px);
}
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-bottom: 20px;
}
.message-row.user {
  flex-direction: row-reverse;
}
.message-avatar {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 11px;
  font-weight: 800;
}
.user .message-avatar {
  color: var(--accent-purple);
  background: rgba(169, 162, 255, 0.13);
}
.message {
  max-width: min(78%, 700px);
  padding: 12px 15px;
  border: 1px solid var(--border);
  border-radius: 4px 15px 15px;
  color: var(--text);
  background: rgba(45, 61, 91, 0.65);
}
.user .message {
  border-radius: 15px 4px 15px 15px;
  border-color: rgba(169, 162, 255, 0.22);
  background: linear-gradient(135deg, rgba(169, 162, 255, 0.16), rgba(112, 183, 255, 0.1));
}
.role-label {
  color: var(--accent-strong);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.user .role-label {
  color: var(--accent-purple);
}
.message p {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
}
.typing {
  display: flex;
  gap: 4px;
  padding: 5px 0;
}
.typing i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.1s infinite ease-in-out;
}
.typing i:nth-child(2) {
  animation-delay: 0.15s;
}
.typing i:nth-child(3) {
  animation-delay: 0.3s;
}
.tool-status {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 4px 0 14px 44px;
  color: var(--accent-strong);
  font-size: 10px;
}
.tool-status span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent);
}
.confirmation-panel {
  margin-top: 13px;
  padding: 14px 16px;
  border-color: rgba(232, 172, 96, 0.35);
}
.confirmation-head {
  display: flex;
  align-items: center;
  gap: 11px;
}
.confirmation-badge {
  flex: 0 0 auto;
  padding: 3px 9px;
  border: 1px solid rgba(232, 172, 96, 0.45);
  border-radius: 999px;
  color: #e8ac60;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
}
.confirmation-head strong {
  display: block;
  color: var(--text);
  font-size: 12px;
}
.confirmation-head small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
}
.confirmation-list {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.confirmation-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.03);
}
.op-tag {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 6px;
  color: #e8ac60;
  background: rgba(232, 172, 96, 0.13);
  font-size: 9px;
  font-weight: 800;
}
.confirmation-detail {
  min-width: 0;
}
.confirmation-detail strong {
  display: block;
  color: var(--text);
  font-size: 11px;
}
.confirmation-detail small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
}
.confirmation-detail code {
  display: block;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 10px;
  word-break: break-all;
}
.confirmation-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 13px;
}
.composer {
  margin-top: 13px;
  padding: 12px;
}
.composer :deep(.el-textarea__inner) {
  min-height: 42px !important;
  padding: 11px 12px;
  border: 0;
  background: transparent !important;
  box-shadow: none !important;
  line-height: 1.6;
}
.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 7px 2px 0 10px;
  border-top: 1px solid var(--border);
}
.composer-footer > span {
  color: var(--text-muted);
  font-size: 9px;
}
.composer-footer .el-button span span {
  margin-left: 8px;
}
.assistant-notice {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 9px;
  text-align: center;
}
@keyframes pulse {
  0%,
  80%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-3px);
  }
}
@media (max-width: 640px) {
  .conversation {
    max-height: none;
  }
  .prompt-grid {
    grid-template-columns: 1fr;
  }
  .message {
    max-width: 86%;
  }
  .composer-footer > span {
    display: none;
  }
  .composer-footer {
    justify-content: flex-end;
  }
}
</style>
