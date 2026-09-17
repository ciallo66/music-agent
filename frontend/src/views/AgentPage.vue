<!-- Agent 对话页面：展示流式回复、工具状态和可复用的提问入口。 -->
<template>
  <section class="agent-page">
    <PageHeader
      eyebrow="智能协作"
      title="智能体"
      subtitle="调用已接入的数据工具，完成检索、分析和可解释的知识问答"
    >
      <template #actions
        ><el-button v-if="messages.length" :disabled="loading" @click="startNewConversation"
          >＋ 新对话</el-button
        ></template
      >
    </PageHeader>

    <div
      v-if="messages.length"
      ref="conversationElement"
      class="conversation page-surface"
      aria-live="polite"
    >
      <div v-for="(item, index) in messages" :key="index" class="message-row" :class="item.role">
        <span class="message-avatar" aria-hidden="true">{{
          item.role === 'user' ? userInitial : '✦'
        }}</span>
        <div class="message">
          <span class="role-label">{{ item.role === 'user' ? '你' : '智能体' }}</span>
          <!-- 用户输入按纯文本展示，模型回复渲染 Markdown。 -->
          <MarkdownContent v-if="item.role === 'assistant'" :content="item.content" />
          <p v-else class="user-text">{{ item.content }}</p>
        </div>
      </div>
      <div v-if="loading && !hasPendingAssistant" class="message-row assistant pending">
        <span class="message-avatar" aria-hidden="true">✦</span>
        <div class="message">
          <span class="role-label">智能体</span>
          <p class="typing"><i></i><i></i><i></i></p>
        </div>
      </div>
      <p v-if="toolStatus" class="tool-status"><span></span>{{ toolStatus }}</p>
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

    <form class="composer" @submit.prevent="sendMessage">
      <el-input
        ref="composerInput"
        v-model="draft"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 5 }"
        maxlength="2000"
        resize="none"
        placeholder="直接输入需求，例如：推荐节奏舒缓、器乐为主的内容"
        :disabled="loading || awaitingConfirmation"
        @keydown="handleComposerKeydown"
      />
      <el-button
        v-if="loading"
        class="send-button"
        native-type="button"
        aria-label="停止分析"
        @click="stopRequest"
      >
        停止
      </el-button>
      <el-button
        v-else
        class="send-button"
        native-type="submit"
        type="primary"
        :disabled="draft.trim().length === 0 || awaitingConfirmation"
        aria-label="发送问题"
      >
        发送
      </el-button>
    </form>
    <p class="assistant-notice">智能回答可能存在偏差，重要信息请结合歌曲详情与实际数据判断。</p>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { ElInput } from 'element-plus'
import { useRoute } from 'vue-router'
import MarkdownContent from '../components/MarkdownContent.vue'
import PageHeader from '../components/PageHeader.vue'
import { parseToolConfirmation, streamAgentChat, streamToolConfirmations } from '../api/agent'
import type { AgentEvent, PendingToolConfirmation } from '../types/agent'
import { showError } from '../utils/feedback'
import { useAuthStore } from '../stores/auth'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const auth = useAuthStore()
const route = useRoute()
const draft = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])
const sessionId = ref<number | null>(null)
const toolStatus = ref('')
const pendingConfirmations = ref<PendingToolConfirmation[]>([])
const conversationElement = ref<HTMLElement | null>(null)
const composerInput = ref<InstanceType<typeof ElInput> | null>(null)
const activeRequest = ref<AbortController | null>(null)
const requestStoppedByUser = ref(false)
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
  run: (onEvent: (event: AgentEvent) => void, signal: AbortSignal) => Promise<number | null>,
  failureHint: string,
): Promise<void> {
  loading.value = true
  toolStatus.value = ''
  const { handle, ensureAssistantText } = createEventHandler()
  const controller = new AbortController()
  activeRequest.value = controller
  requestStoppedByUser.value = false
  let timedOut = false
  const timeoutId = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, 90_000)
  await scrollToLatest()
  try {
    const returnedSessionId = await run(handle, controller.signal)
    if (returnedSessionId !== null) sessionId.value = returnedSessionId
    ensureAssistantText()
  } catch (error) {
    if (timedOut) showError('分析等待超时，请重新发送')
    else if (!requestStoppedByUser.value) showError(error, failureHint)
  } finally {
    window.clearTimeout(timeoutId)
    if (activeRequest.value === controller) activeRequest.value = null
    loading.value = false
    toolStatus.value = ''
    await scrollToLatest()
  }
}

// 允许用户结束无响应的流式请求，避免输入区长期锁死。
function stopRequest(): void {
  requestStoppedByUser.value = true
  activeRequest.value?.abort()
}

// 发送消息并消费 SSE；文本增量直接更新最后一条助手消息。
async function sendMessage(): Promise<void> {
  const message = draft.value.trim()
  if (!message || loading.value || awaitingConfirmation.value) return
  messages.value.push({ role: 'user', content: message })
  draft.value = ''
  await consumeStream(
    (onEvent, signal) => streamAgentChat({ message, sessionId: sessionId.value, onEvent, signal }),
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
    (onEvent, signal) =>
      streamToolConfirmations({ sessionId: currentSessionId, decisions, onEvent, signal }),
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

// 清空当前展示和会话 ID，下一次提问会创建新会话。
function startNewConversation(): void {
  activeRequest.value?.abort()
  messages.value = []
  sessionId.value = null
  toolStatus.value = ''
  draft.value = ''
  pendingConfirmations.value = []
  void nextTick(() => composerInput.value?.focus())
}

// Enter 发送、Shift+Enter 换行；输入法组合期间不抢占回车。
function handleComposerKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void sendMessage()
}

// 页面创建后提交从其它页面带入的话题（如推荐卡片的“在智能体中继续”）。
onMounted(async () => {
  const topic = typeof route.query.topic === 'string' ? route.query.topic : ''
  await nextTick()
  composerInput.value?.focus()
  if (!topic.trim()) return
  draft.value = topic
  await sendMessage()
})

onBeforeUnmount(() => activeRequest.value?.abort())
</script>

<style scoped>
.agent-page {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: var(--page-gutter);
}
.conversation {
  min-height: 260px;
  max-height: calc(100vh - 310px);
  flex: 1;
  padding: clamp(18px, 3vw, 34px);
  overflow-y: auto;
  overscroll-behavior: contain;
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
  position: relative;
  width: min(100%, 860px);
  align-self: center;
  margin-top: 13px;
}
.composer :deep(.el-textarea__inner) {
  min-height: 52px !important;
  padding: 14px 96px 14px 16px;
  line-height: 1.6;
}
.send-button {
  position: absolute;
  right: 7px;
  bottom: 7px;
  min-width: 76px;
  height: 38px;
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
  .message {
    max-width: 86%;
  }
  .composer :deep(.el-textarea__inner) {
    padding-right: 82px;
  }
  .send-button {
    min-width: 66px;
  }
}
</style>
