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
      <div class="conversation-inner">
        <!-- 运行状态条：吸顶显示「正在分析 / 正在调用工具 / 正在生成」，随时知道智能体在干什么 -->
        <p v-if="runStatus" class="run-status" role="status">
          <i aria-hidden="true"></i>{{ runStatus }}
        </p>
        <div v-for="(item, index) in messages" :key="index" class="message-row" :class="item.role">
          <span class="message-avatar" aria-hidden="true">{{
            item.role === 'user' ? userInitial : '✦'
          }}</span>
          <div class="message">
            <!-- 用户输入按纯文本展示，模型回复渲染 Markdown。 -->
            <MarkdownContent v-if="item.role === 'assistant'" :content="item.content" />
            <p v-else class="user-text">{{ item.content }}</p>
            <!-- 正在流式输出时，在最后一条回复末尾显示光标。 -->
            <span
              v-if="item.role === 'assistant' && loading && index === messages.length - 1"
              class="stream-cursor"
              aria-hidden="true"
            />
          </div>
        </div>
        <div v-if="loading && !hasPendingAssistant" class="message-row assistant pending">
          <span class="message-avatar" aria-hidden="true">✦</span>
          <div class="message">
            <p class="typing"><i></i><i></i><i></i></p>
          </div>
        </div>
        <p v-if="toolStatus" class="tool-status"><span></span>{{ toolStatus }}</p>
      </div>
    </div>

    <div v-else class="agent-empty page-surface">
      <div class="empty-copy">
        <span class="empty-mark" aria-hidden="true">✦</span>
        <h2>今天想分析点什么？</h2>
        <p>我可以调用已接入的数据工具，完成检索、特征分析与知识问答。</p>
      </div>
      <div class="suggestion-grid">
        <button
          v-for="item in suggestions"
          :key="item"
          type="button"
          class="suggestion-card"
          @click="sendSuggestion(item)"
        >
          {{ item }}
        </button>
      </div>
    </div>

    <div v-if="awaitingConfirmation" class="confirmation-panel page-surface">
      <div class="confirmation-head">
        <span class="confirmation-badge">需确认</span>
        <strong>以下操作会写入数据，确认后才执行</strong>
        <div class="confirmation-actions">
          <el-button
            size="small"
            :disabled="loading || Boolean(firstDecision)"
            @click="respondToConfirmations(false)"
          >
            拒绝
          </el-button>
          <el-button
            size="small"
            type="primary"
            :loading="loading"
            :disabled="Boolean(firstDecision)"
            @click="respondToConfirmations(true)"
          >
            确认执行
          </el-button>
        </div>
      </div>
      <ul class="confirmation-list">
        <li
          v-for="item in pendingConfirmations"
          :key="item.confirmationId"
          :class="{ decided: decisionOf(item.confirmationId) !== '' }"
        >
          <span class="op-tag">{{ operationLabel(item.operation) }}</span>
          <div class="confirmation-detail">
            <strong>{{ confirmationTitle(item) }}</strong>
            <dl v-if="confirmationFacts(item).length" class="confirmation-facts">
              <div v-for="fact in confirmationFacts(item)" :key="fact.label">
                <dt>{{ fact.label }}</dt>
                <dd>{{ fact.value }}</dd>
              </div>
            </dl>
          </div>
          <span v-if="decisionOf(item.confirmationId)" class="decision-chip">
            {{ decisionOf(item.confirmationId) }}
          </span>
        </li>
      </ul>
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
        :disabled="awaitingConfirmation"
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
      <!-- 运行中用户仍可打字：明确告诉他这条会在本轮结束后才能发出 -->
      <p v-if="loading && draft.trim()" class="composer-busy">
        智能体正在运行，这条将在本轮结束后发送
      </p>
    </form>
    <div class="composer-foot">
      <p class="assistant-notice">智能回答可能存在偏差，重要信息请结合详情与实际数据判断。</p>
      <p class="composer-hint">Enter 发送 · Shift + Enter 换行 · 最多 2000 字</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
// 已作出的决定：确认后按钮要禁用、卡片转为「已确认」状态，不能还能再点一次。
const confirmationDecisions = ref<Record<number, string>>({})
const conversationElement = ref<HTMLElement | null>(null)
const composerInput = ref<InstanceType<typeof ElInput> | null>(null)
const activeRequest = ref<AbortController | null>(null)
const requestStoppedByUser = ref(false)
// 是否自动跟随到最新消息：用户上滚翻历史时暂停，滚回底部后恢复。
const autoFollow = ref(true)
// 内容高度变化时自动滚到底（流式输出、工具状态、确认卡片都会触发）。
let resizeObserver: ResizeObserver | null = null
// 一帧内只滚一次，避免滚动 ↔ ResizeObserver 互相触发。
let scrollScheduled = false
const userInitial = computed(() => auth.user?.username.slice(0, 1).toUpperCase() || '你')
const hasPendingAssistant = computed(
  () => messages.value[messages.value.length - 1]?.role === 'assistant',
)
// 运行状态：让用户随时知道智能体现在在干什么（正在分析 / 正在调用工具 / 正在生成）。
const runStatus = computed(() => {
  if (awaitingConfirmation.value) return '等待你确认高风险操作'
  if (!loading.value) return ''
  if (toolStatus.value.startsWith('工具调用失败')) return toolStatus.value
  if (toolStatus.value && !toolStatus.value.startsWith('有高风险')) return toolStatus.value
  return hasPendingAssistant.value ? '正在生成回答…' : '正在分析你的问题…'
})

// 有未确认的高风险操作时，先让用户处理完再继续对话。
const awaitingConfirmation = computed(() => pendingConfirmations.value.length > 0)
// 已经有决定时（按钮已点过），关闭按钮避免重复提交。
const firstDecision = computed(() => {
  const first = pendingConfirmations.value[0]
  return first ? (confirmationDecisions.value[first.confirmationId] ?? '') : ''
})

/** 读取某条确认的决定状态文案。 */
function decisionOf(confirmationId: number): string {
  return confirmationDecisions.value[confirmationId] ?? ''
}

/** 把工具参数转成用户看得懂的事实项，不暴露工具名和 JSON。 */
function confirmationFacts(item: PendingToolConfirmation): { label: string; value: string }[] {
  const args = item.arguments ?? {}
  const facts: { label: string; value: string }[] = []
  const push = (label: string, value: unknown): void => {
    if (typeof value === 'string' && value.trim()) facts.push({ label, value: value.trim() })
    else if (typeof value === 'number') facts.push({ label, value: String(value) })
  }
  push('名称', args.name)
  push('描述', args.description)
  push('集合', args.playlist_name)
  push('歌曲', Array.isArray(args.song_ids) ? `共 ${args.song_ids.length} 首` : undefined)
  if (!facts.length && item.reason) facts.push({ label: '说明', value: item.reason })
  return facts
}

// 空状态下的示例问题，点击即发送，降低首次使用门槛。
const suggestions = [
  '帮我找几首适合深夜听的歌',
  '分析这首歌为什么听起来比较忧郁',
  'City Pop 是什么风格？',
  '我最近听的歌有什么共同特点？',
]

// 只有消息列表内部滚动（和主流对话产品一致）：输入框固定在底部不随消息滚走。
// 页面用 ResizeObserver 盯着内容高度，新内容出现就滚到底部。
async function scrollToLatest(): Promise<void> {
  await nextTick()
  const surface = conversationElement.value
  // 单飞保护：ResizeObserver 每次高度变化都会触发，滚动本身也可能引发新的高度变化，
  // 用一帧只滚一次的阀门避免滚动与观察者互相踢成死循环（会把主线程卡住）。
  if (surface === null || !autoFollow.value || scrollScheduled) return
  scrollScheduled = true
  requestAnimationFrame(() => {
    scrollScheduled = false
    surface.scrollTo({ top: surface.scrollHeight })
  })
}

/** 用户自己在翻历史时不抢滚动条；滚回底部后恢复自动跟随。 */
function handleSurfaceScroll(): void {
  const surface = conversationElement.value
  if (surface === null) return
  const distanceToBottom = surface.scrollHeight - surface.scrollTop - surface.clientHeight
  autoFollow.value = distanceToBottom <= 120
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

// 点击示例问题时填入输入框并直接发送。
async function sendSuggestion(text: string): Promise<void> {
  if (loading.value) return
  draft.value = text
  await sendMessage()
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

// 待确认内容用人话展示：不把工具名和 JSON 抛给用户。
// 标题是「这次要做什么」，明细是具体内容（名称、描述等）。
function confirmationTitle(item: PendingToolConfirmation): string {
  const args = item.arguments ?? {}
  if (item.name === 'create_playlist') return `新建集合「${String(args.name ?? '未命名')}」`
  if (item.name === 'add_song_to_playlist') {
    return `把歌曲加入集合「${String(args.playlist_name ?? args.playlist_id ?? '')}」`
  }
  if (item.name === 'delete_playlist')
    return `删除集合「${String(args.name ?? args.playlist_id ?? '')}」`
  return item.reason || '需要你确认后才能执行'
}

// 明细改由 confirmationFacts 提供（键值对），这里不再输出原始 JSON。

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
  // 运行中回车不发送：此时按钮是「停止」，要中断请点按钮，避免误触
  if (loading.value || awaitingConfirmation.value) return
  event.preventDefault()
  void sendMessage()
}

// 页面创建后提交从其它页面带入的话题（如推荐卡片的“在智能体中继续”）。
onMounted(async () => {
  // 锁住外层滚动：本页只允许消息列表内部滚动，避免两条滚动条。
  document.querySelector('.main-content')?.classList.add('main-content--locked')
  const topic = typeof route.query.topic === 'string' ? route.query.topic : ''
  await nextTick()
  composerInput.value?.focus()
  if (!topic.trim()) return
  draft.value = topic
  await sendMessage()
})

// 释放本页对整站的影响：解锁外层滚动、断开观察者、终止在途请求。
// 抽成独立函数是为了让路由守卫也能兜底调用 —— 万一组件卸载没跑到，
// 外面的滚动锁会一直留着，导致切到别的页面后整页滚不动。
function releasePageLocks(): void {
  resizeObserver?.disconnect()
  resizeObserver = null
  document.querySelector('.main-content')?.classList.remove('main-content--locked')
  activeRequest.value?.abort()
  activeRequest.value = null
  loading.value = false
}

onBeforeUnmount(releasePageLocks)
defineExpose({ releasePageLocks })

// 消息列表出现/消失时接管滚动：内部滚动 + 内容变化自动跟随到底部。
watch(conversationElement, (element) => {
  resizeObserver?.disconnect()
  resizeObserver = null
  element?.removeEventListener('scroll', handleSurfaceScroll)
  if (element === null) return
  element.addEventListener('scroll', handleSurfaceScroll, { passive: true })
  resizeObserver = new ResizeObserver(() => void scrollToLatest())
  resizeObserver.observe(element)
  autoFollow.value = true
  void scrollToLatest()
})
</script>

<style scoped>
/* 本页不允许外层滚动：整页高度锁在一屏内，滚动只发生在消息列表内部。
   两层都要管住——外层容器禁用滚动，本页自身撑满而不溢出。 */
:global(.main-content--locked) {
  overflow-y: hidden;
}
:global(.main-content--locked .content-frame) {
  height: 100%;
}
.agent-page {
  display: flex;
  /* 本页对话宽度：比输入框更宽，减少左右空白 */
  --chat-width: 1080px;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  padding: var(--page-gutter);
}
/* 对话区撑满剩余高度；滚动在消息列表内部进行 */
.conversation,
.agent-empty {
  min-height: 0;
  flex: 1;
}
.conversation {
  min-height: 0;
  flex: 1;
  padding: clamp(18px, 2.4vw, 30px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
/* 内容宽度与下方输入区对齐，宽屏下不再两侧各空一大块 */
.conversation-inner {
  display: flex;
  width: 100%;
  max-width: var(--chat-width);
  flex-direction: column;
  margin: 0 auto;
}
/* 运行状态条：吸顶，滚动时也能看到智能体当前在做什么 */
.run-status {
  position: sticky;
  z-index: 1;
  top: -8px;
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 8px;
  margin: 0 0 16px;
  padding: 6px 12px 6px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--surface);
  backdrop-filter: blur(6px);
  font-size: 11px;
  line-height: 1.2;
}
.run-status i {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: run-pulse 1.2s ease-in-out infinite;
}
@keyframes run-pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 26px;
}
.message-row:last-child {
  margin-bottom: 2px;
}
.message-row.user {
  flex-direction: row-reverse;
}
.message-avatar {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  margin-top: 2px;
  place-items: center;
  border-radius: 9px;
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 12px;
  font-weight: 800;
}
.user .message-avatar {
  color: var(--accent-purple);
  background: rgba(169, 162, 255, 0.15);
}
/* 助手消息不再套气泡：直接排在背景上，读起来是对话而不是卡片列表 */
.message {
  max-width: 100%;
  min-width: 0;
  padding: 0;
  color: var(--text);
  background: none;
}
/* 只给用户消息保留气泡，突出「我说的话」 */
.user .message {
  max-width: min(76%, 720px);
  padding: 10px 14px;
  border: 1px solid rgba(169, 162, 255, 0.22);
  border-radius: 14px 4px 14px 14px;
  background: linear-gradient(135deg, rgba(169, 162, 255, 0.16), rgba(112, 183, 255, 0.1));
}
/* 流式输出光标：让用户看出「正在生成」 */
.stream-cursor {
  display: inline-block;
  width: 7px;
  height: 15px;
  margin-left: 3px;
  border-radius: 2px;
  background: var(--accent);
  vertical-align: text-bottom;
}
@media (prefers-reduced-motion: no-preference) {
  .stream-cursor {
    animation: cursor-blink 1s ease-in-out infinite;
  }
}
@keyframes cursor-blink {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.15;
  }
}
/* 空状态：居中引导 + 示例问题，降低首次使用门槛 */
.agent-empty {
  display: flex;
  min-height: 340px;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 28px;
  padding: clamp(28px, 5vw, 56px);
}
.empty-copy {
  width: 100%;
  max-width: var(--chat-width);
  text-align: center;
}
.empty-mark {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  margin: 0 auto 16px;
  border-radius: 14px;
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 20px;
}
.empty-copy h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(20px, 3vw, 26px);
  letter-spacing: -0.02em;
}
.empty-copy p {
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
}
.suggestion-grid {
  display: grid;
  width: 100%;
  max-width: var(--chat-width);
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.suggestion-card {
  padding: 13px 15px;
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text-secondary);
  background: var(--surface);
  font-family: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease,
    transform 0.15s ease;
}
.suggestion-card:hover {
  border-color: var(--border-strong);
  color: var(--text);
  background: var(--surface-hover);
  transform: translateY(-1px);
}
.suggestion-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 640px) {
  .suggestion-grid {
    grid-template-columns: 1fr;
  }
}
.message p {
  margin: 0;
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
/* 工具调用状态：做成小胶囊，像主流的“正在执行…”提示，而不是一行裸文字 */
.tool-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px 40px;
  padding: 6px 12px 6px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--surface);
  font-size: 11px;
  line-height: 1.2;
}
.tool-status span {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(112, 183, 255, 0.6);
  animation: tool-pulse 1.4s ease-out infinite;
}
@keyframes tool-pulse {
  70% {
    box-shadow: 0 0 0 7px rgba(112, 183, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(112, 183, 255, 0);
  }
}
.confirmation-panel {
  width: min(100%, var(--chat-width));
  margin: 13px auto 0;
  padding: 10px 14px;
  border-color: rgba(232, 172, 96, 0.35);
}
/* 标题与按钮同一行：需要操作时按钮就在眼前，不用往下找 */
.confirmation-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.confirmation-badge {
  flex: 0 0 auto;
  padding: 3px 9px;
  border: 1px solid rgba(232, 172, 96, 0.45);
  border-radius: 999px;
  color: #e8ac60;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.06em;
}
.confirmation-head strong {
  min-width: 0;
  flex: 1;
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
}
.confirmation-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}
.confirmation-list {
  display: grid;
  gap: 6px;
  margin: 9px 0 0;
  padding: 0;
  list-style: none;
}
.confirmation-list li {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.03);
}
.op-tag {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 6px;
  color: #e8ac60;
  background: rgba(232, 172, 96, 0.13);
  font-size: 10px;
  font-weight: 700;
}
.confirmation-detail {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
}
.confirmation-detail strong {
  color: var(--text);
  font-size: 11px;
  font-weight: 600;
}
.confirmation-detail code {
  min-width: 0;
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  word-break: break-all;
}
.confirmation-detail small {
  width: 100%;
  color: var(--text-muted);
  font-size: 10px;
}
.composer {
  position: relative;
  flex: 0 0 auto;
  width: min(100%, var(--chat-width));
  align-self: center;
  margin-top: 14px;
  border: 1px solid var(--border-strong);
  border-radius: 16px;
  background: var(--surface);
  box-shadow: 0 10px 30px rgba(8, 15, 30, 0.28);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
/* 聚焦时给出明确反馈，和主流对话产品一致 */
.composer:focus-within {
  border-color: var(--accent);
  box-shadow:
    0 10px 30px rgba(8, 15, 30, 0.32),
    0 0 0 3px var(--accent-soft);
}
.composer :deep(.el-textarea__inner) {
  min-height: 56px !important;
  padding: 16px 62px 16px 16px;
  border: none;
  background: transparent;
  box-shadow: none;
  font-size: 13px;
  line-height: 1.7;
}
.send-button {
  position: absolute;
  right: 10px;
  bottom: 10px;
  width: 40px;
  min-width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 12px;
  font-size: 12px;
}
.composer-busy {
  margin: 6px 2px 0;
  color: var(--accent);
  font-size: 10px;
  line-height: 1.4;
}
.composer-foot {
  display: flex;
  flex: 0 0 auto;
  width: min(100%, var(--chat-width));
  align-self: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 4px 12px;
  margin-top: 8px;
}
.assistant-notice,
.composer-hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.5;
}
.composer-hint {
  color: var(--text-faint, var(--text-muted));
  opacity: 0.85;
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
