<!-- Agent 对话页面：展示流式回复、工具状态和可复用的提问入口。 -->
<template>
  <section class="agent-page">
    <div class="agent-shell" :class="{ 'side-open': sessionsOpen }">
      <!-- 左侧会话栏：仿主流对话产品的抽屉式侧栏。
           收起时整条滑出画面（宽度归零），主区域自动吃掉全部宽度；
           开关固定在页头左上角，展开/收起都是同一个位置。 -->
      <aside class="session-drawer" aria-label="历史对话" :aria-hidden="!sessionsOpen">
        <div class="drawer-inner">
          <div class="drawer-head">
            <button
              type="button"
              class="drawer-new"
              :disabled="loading"
              title="开始新对话"
              @click="newConversation"
            >
              <span aria-hidden="true">＋</span> 新对话
            </button>
          </div>

          <p class="drawer-label">历史对话</p>
          <p v-if="sessionsLoading" class="session-state">正在读取…</p>
          <p v-else-if="sessions.length === 0" class="session-state">
            还没有记录。问点什么，这里会自动留下对话。
          </p>
          <ul v-else class="session-list">
            <li v-for="item in sessions" :key="item.id" :class="{ active: item.id === sessionId }">
              <button
                type="button"
                class="session-item"
                :disabled="loading"
                :title="sessionTitle(item)"
                @click="selectSession(item)"
              >
                <span class="session-title">{{ sessionTitle(item) }}</span>
                <span class="session-meta">
                  {{ formatSessionTime(item.created_at) }} · {{ item.message_count }} 条
                </span>
              </button>
              <button
                type="button"
                class="session-remove"
                :disabled="loading"
                :aria-label="`删除对话「${sessionTitle(item)}」`"
                @click.stop="removeSession(item)"
              >
                ×
              </button>
            </li>
          </ul>
        </div>
      </aside>

      <div class="agent-main">
        <!-- 不设页头：标题与说明在这里没有信息价值，只会占掉一条对话高度。
             会话栏开关只渲染一份，绝对定位悬浮在主区左上角，不占任何布局高度。 -->
        <button
          type="button"
          class="drawer-toggle"
          :aria-expanded="sessionsOpen"
          :title="sessionsOpen ? '收起历史对话' : '展开历史对话'"
          @click="sessionsOpen = !sessionsOpen"
        >
          <AppIcon name="menu" :size="16" />
        </button>
        <div class="agent-body">
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
              <div
                v-for="(item, index) in messages"
                :key="index"
                class="message-row"
                :class="item.role"
              >
                <span class="message-role">{{ item.role === 'user' ? '你' : '助手' }}</span>
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
                <span class="message-role">助手</span>
                <div class="message">
                  <p class="typing"><i></i><i></i><i></i></p>
                </div>
              </div>
              <p v-if="toolStatus" class="tool-status"><span></span>{{ toolStatus }}</p>
            </div>
          </div>

          <div v-else class="agent-empty page-surface">
            <div class="empty-copy">
              <h2>今天想分析点什么？</h2>
              <p>我可以调用已接入的数据工具，完成检索、特征分析与知识问答。</p>
            </div>
            <div class="suggestion-grid">
              <button
                v-for="(item, index) in suggestions"
                :key="item"
                type="button"
                class="suggestion-card"
                @click="sendSuggestion(item)"
              >
                <span class="suggestion-index numeric">{{
                  String(index + 1).padStart(2, '0')
                }}</span>
                <span>{{ item }}</span>
                <AppIcon name="arrow-right" :size="14" class="suggestion-arrow" />
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

          <!-- 输入区固定在整列最底部：它是 agent-body 的最后一层，
             消息区（.conversation）用 flex 吃掉剩下的全部高度，
             两边不再互相挤。 -->
          <form class="composer" @submit.prevent="sendMessage">
            <el-input
              ref="composerInput"
              v-model="draft"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 6 }"
              maxlength="2000"
              resize="none"
              placeholder="描述你想找的内容，例如：节奏舒缓的器乐"
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
            <!-- 待确认时输入被禁用，明确说明为什么不能输入 -->
            <p v-if="awaitingConfirmation" class="composer-busy">
              先处理上方的确认操作，再继续提问
            </p>
          </form>

          <div class="composer-foot">
            <p class="assistant-notice">智能回答可能存在偏差，重要信息请结合详情与实际数据判断。</p>
            <p class="composer-hint">Enter 发送 · Shift + Enter 换行 · 最多 2000 字</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ElInput } from 'element-plus'
import { useRoute } from 'vue-router'
import MarkdownContent from '../components/MarkdownContent.vue'
import AppIcon from '../components/AppIcon.vue'
import {
  deleteAgentSession,
  getAgentSession,
  listAgentSessions,
  parseToolConfirmation,
  streamAgentChat,
  streamToolConfirmations,
} from '../api/agent'
import type { AgentEvent, AgentSessionSummary, PendingToolConfirmation } from '../types/agent'
import { showError } from '../utils/feedback'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const route = useRoute()
const draft = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])
const sessionId = ref<number | null>(null)
// 历史会话列表：刷新页面后仍能找回之前的对话。窄屏默认收起，把宽度让给对话。
const sessions = ref<AgentSessionSummary[]>([])
const sessionsLoading = ref(false)
// 会话栏开合状态：记住用户上次的选择（刷新后不再自己弹开）。
// 没有保存过偏好时按屏宽决定：窄屏（≤1100px）抽屉是浮层、会盖住左上角的悬浮开关，默认收起。
const SESSIONS_OPEN_KEY = 'music-agent:agent-drawer-open'

function readSessionsOpen(): boolean {
  try {
    const saved = window.localStorage.getItem(SESSIONS_OPEN_KEY)
    if (saved !== null) return saved === '1'
  } catch {
    // 隐私模式下不可用：退回按屏宽决定
  }
  return window.innerWidth > 1100
}

const sessionsOpen = ref(readSessionsOpen())

watch(sessionsOpen, (open) => {
  try {
    window.localStorage.setItem(SESSIONS_OPEN_KEY, open ? '1' : '0')
  } catch {
    // 存不下就算了，不影响使用
  }
})

// 窄屏抽屉是浮层：选完会话或新建后自动收起，否则会一直盖住对话
function closeDrawerOnNarrow(): void {
  if (window.innerWidth <= 1100) sessionsOpen.value = false
}
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
    // 一轮结束后刷新历史列表：新会话会带着首条提问出现在侧栏
    if (sessionId.value !== null) await loadSessions()
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

// 抽屉里的「新对话」：桌面保持抽屉展开，窄屏浮层选完自动收起
function newConversation(): void {
  startNewConversation()
  closeDrawerOnNarrow()
}

// 抽屉里的历史会话：同上，窄屏点完就收起，桌面保持原样
async function selectSession(item: AgentSessionSummary): Promise<void> {
  await openSession(item)
  closeDrawerOnNarrow()
}

// 会话列表标题：没有用户消息的会话（建完就走）给一个兜底文案。
function sessionTitle(item: AgentSessionSummary): string {
  const title = item.title?.replace(/\s+/g, ' ').trim() ?? ''
  if (!title) return '新对话'
  return title.length > 22 ? `${title.slice(0, 22)}…` : title
}

// 会话时间按「今天 / 昨天 / 日期」展示，比完整时间戳更好扫。
function formatSessionTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  const sameDay = date.toDateString() === now.toDateString()
  if (sameDay) return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) return '昨天'
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`
}

// 拉取历史会话列表；失败不打断对话，只留空列表。
async function loadSessions(): Promise<void> {
  sessionsLoading.value = true
  try {
    const { data } = await listAgentSessions()
    sessions.value = data
  } catch {
    sessions.value = []
  } finally {
    sessionsLoading.value = false
  }
}

// 打开一个历史会话：把服务端存的原文读回来铺进消息区。
async function openSession(item: AgentSessionSummary): Promise<void> {
  if (loading.value || item.id === sessionId.value) return
  activeRequest.value?.abort()
  pendingConfirmations.value = []
  confirmationDecisions.value = {}
  try {
    const { data } = await getAgentSession(item.id)
    sessionId.value = data.id
    messages.value = data.messages.map((message) => ({
      role: message.role,
      content: message.content,
    }))
    toolStatus.value = ''
    await scrollToLatest()
  } catch (error) {
    showError(error, '这段对话暂时打不开')
  }
}

// 删除一个历史会话；删的是当前打开的会话时顺手清屏。
async function removeSession(item: AgentSessionSummary): Promise<void> {
  if (loading.value) return
  try {
    await deleteAgentSession(item.id)
    sessions.value = sessions.value.filter((session) => session.id !== item.id)
    if (item.id === sessionId.value) startNewConversation()
  } catch (error) {
    showError(error, '删除对话失败')
  }
}

// 页面创建后提交从其它页面带入的话题（如推荐卡片的“在智能体中继续”）。
onMounted(async () => {
  // 滚动锁由外壳按路由标记在渲染阶段加上（见 MainLayout 的 isFullHeightPage），
  // 这里不再用命令式加类：那会晚一帧生效，切换页面时先闪一下前台骨架。
  const topic = typeof route.query.topic === 'string' ? route.query.topic : ''
  await nextTick()
  composerInput.value?.focus()
  // 先恢复历史：有记录就把最近一段对话铺出来，刷新页面不再丢上下文。
  await loadSessions()
  if (!topic.trim() && sessions.value.length > 0) {
    await openSession(sessions.value[0])
  }
  if (!topic.trim()) return
  draft.value = topic
  await sendMessage()
})

// Enter 发送、Shift+Enter 换行；输入法组合期间不抢占回车。
function handleComposerKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  // 运行中回车不发送：此时按钮是「停止」，要中断请点按钮，避免误触
  if (loading.value || awaitingConfirmation.value) return
  event.preventDefault()
  void sendMessage()
}

// 释放本页对整站的影响：断开观察者、终止在途请求。
// 滚动锁已经改由外壳按路由标记控制，这里不再操作 .main-content 的类。
function releasePageLocks(): void {
  resizeObserver?.disconnect()
  resizeObserver = null
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
/* 整页锁一屏：外壳（MainLayout）按路由 meta.fullHeight 在渲染阶段就打上
   .main-content--locked，这里只需要保证本页填满内容区、不产生外层滚动。 */
:global(.main-content--locked .content-frame > *) {
  min-height: 0;
}
.agent-page {
  /* 抽屉宽度（窄屏浮层与展开动画都用它） */
  --drawer-width: 244px;
  /* flex:1 + min-height:0 撑满内容区并允许收缩，height:100% 只是非 flex 父容器时的兜底。
     两者都写是因为 height:100% 在父高为 auto 时不生效，会出现「输入框下面空一大块」。 */
  box-sizing: border-box;
  height: 100%;
  min-height: 0;
  flex: 1;
  padding: var(--page-gutter);
}
/* 抽屉 + 主区：整页一行 flex。
   align-items: stretch 让两侧都吃满整列高度：历史对话面板顶部/底部与对话卡片对齐，
   之前用 center 时抽屉是内容高度（8 条约 514px）被垂直居中，上下各差一截，看着就散。 */
.agent-shell {
  display: flex;
  /* 关键：必须自己撑满内容区（父级是 flex 纵向容器，只写 height 会被内容撑宽），
     否则「对话列居中」是相对一个被内容撑出来的宽度算的，视觉上仍然偏右。 */
  width: 100%;
  height: 100%;
  min-height: 0;
  align-items: stretch;
  gap: 0;
  transition: gap 0.2s ease;
}
.agent-shell.side-open {
  gap: 24px;
}
/* 会话抽屉：宽度动画开合，像主流对话产品的左侧栏。
   高度与右侧对话卡片精确等高：卡片下方固定是「输入区 + 提示行」这一块（实测 117px），
   所以抽屉高度 = 整列高度 − 这一块。以前它要么是内容高度（被居中，上下各差一截），
   要么拉到整列高度（比卡片长一截），两种都和卡片对不齐。 */
.agent-shell {
  --drawer-inset-bottom: 117px;
}
.session-drawer {
  width: 0;
  min-height: 0;
  height: calc(100% - var(--drawer-inset-bottom));
  flex-shrink: 0;
  overflow: hidden;
  transition:
    width 0.22s ease,
    opacity 0.18s ease;
  opacity: 0;
}
.agent-shell.side-open .session-drawer {
  width: var(--drawer-width);
  opacity: 1;
}
.drawer-inner {
  display: flex;
  height: 100%;
  flex-direction: column;
  gap: 8px;
  padding: 10px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  overflow-y: auto;
  overscroll-behavior: contain;
}
/* 主区：对话 + 输入，撑满抽屉之外的全部宽度；没有页头，纵向全给对话。
   整列封顶并居中：对话卡片、输入框、提示行都由它统一宽度，
   三者永远同宽同轴 —— 不会出现「上面一张宽带子、下面一个窄框」的错位。
   1040px 是主流对话产品的正文列宽，再宽反而不利于阅读。 */
.agent-main {
  position: relative; /* 悬浮的会话栏开关以这里为定位基准 */
  display: flex;
  /* 必须自己有确定高度：外壳用 align-items:center，列不会被拉伸，
     一旦高度变成 auto，下面的 flex:1 消息区就会被内容撑高，
     把输入框顶出视口（踩过这个坑）。 */
  height: 100%;
  max-height: 100%;
  max-width: 1040px;
  min-width: 0;
  min-height: 0;
  /* 缺省 1040px，空间不够时才收缩；margin auto 负责居中 */
  flex: 0 1 1040px;
  flex-direction: column;
  margin: 0 auto;
}
/* 会话栏开关：悬浮在对话卡片左上角，不占布局高度 */
.drawer-toggle {
  position: absolute;
  z-index: 4;
  top: 10px;
  left: 10px;
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  opacity: 0.75;
  transition: opacity 0.15s ease;
}
.drawer-toggle:hover {
  opacity: 1;
  color: var(--text);
  background: var(--surface-hover);
}
.drawer-head {
  flex-shrink: 0;
}
.drawer-new {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  background: var(--surface);
  cursor: pointer;
  font-family: inherit;
  font-size: var(--fs-xs);
}
.drawer-new:hover:not(:disabled) {
  background: var(--surface-hover);
}
.drawer-new:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.drawer-label {
  margin: 4px 4px 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.agent-body {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}
.session-state {
  margin: 4px 2px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.7;
}
.session-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.session-list li {
  position: relative;
  display: flex;
  align-items: stretch;
  border: 1px solid transparent;
  border-radius: 10px;
}
.session-list li:hover {
  border-color: var(--border);
  background: var(--surface-hover);
}
.session-list li.active {
  border-color: var(--border-strong);
  background: var(--accent-soft);
}
.session-item {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
  padding: 8px 26px 8px 10px;
  border: 0;
  border-radius: 10px;
  color: inherit;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.session-item:disabled {
  cursor: not-allowed;
}
.session-title {
  overflow: hidden;
  color: var(--text);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-meta {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.session-remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  /* 常态隐藏：侧栏只有一两条会话时，常显的 × 会让面板显得杂乱；
     悬停或键盘聚焦时再出现，仍然可发现。 */
  opacity: 0;
  transition: opacity 0.15s ease;
}
.session-list li:hover .session-remove,
.session-remove:focus-visible {
  opacity: 1;
}
.session-remove:hover {
  color: #ff9c9c;
  background: rgba(255, 120, 120, 0.14);
}
.session-remove:disabled {
  cursor: not-allowed;
}
/* 窄屏：抽屉改成浮层，展开时盖在对话上，不挤压内容宽度。
   浮层 z-index 高于悬浮开关，所以开关要右移让开抽屉，否则点不到（实测踩到过）。 */
@media (max-width: 1100px) {
  .agent-shell {
    position: relative;
  }
  .session-drawer {
    position: absolute;
    z-index: 6;
    top: 0;
    bottom: 0;
    left: 0;
    /* 浮层模式覆盖整个对话区，不再按卡片高度收缩 */
    height: 100%;
    box-shadow: var(--shadow-soft);
  }
  .agent-shell.side-open .session-drawer {
    width: 260px;
  }
  .agent-shell.side-open .drawer-toggle {
    left: 274px;
  }
}
/* 对话区撑满剩余高度；滚动在消息列表内部进行 */
.conversation,
.agent-empty {
  position: relative;
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  /* 内容从顶部开始排：以前这里是 center，消息少时整段被垂直居中，
     上下各留一大条空白，用户看到的就是「挤」和「一堆空白」 */
  justify-content: flex-start;
  align-items: stretch;
}
.conversation {
  /* 顶部留出悬浮开关的位置，第一条消息不被它压住 */
  padding: 52px 0 18px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
/* 左右内边距给到内容层：卡片边到消息之间留白，
   宽度仍与输入框同宽（内边距不影响卡片外框对齐） */
.conversation-inner {
  display: flex;
  width: 100%;
  flex-direction: column;
  padding: 0 clamp(16px, 1.8vw, 26px);
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
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  font-size: var(--fs-xs);
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
/* 消息按「说话人 + 内容」两行排：不做头像、不做左右气泡，
   读起来像一份对话记录，而不是聊天模板。 */
.message-row {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 26px;
}
.message-row:last-child {
  margin-bottom: 2px;
}
.message-role {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.message {
  max-width: 100%;
  min-width: 0;
  padding: 0;
  color: var(--text);
  background: none;
}
/* 助手回复限制阅读宽度：1040px 的长段落每行太多字，读起来累 */
.assistant .message {
  max-width: 760px;
}
/* 用户消息给一块浅底，区分「我说的话」；助手回复直接排在页面底色上。 */
.user .message {
  max-width: min(76%, 720px);
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-raised);
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
/* 空状态：左对齐的引导 + 一组编号示例，像「查询示例」而不是 AI 灵感卡片 */
.agent-empty {
  align-items: flex-start;
  justify-content: center;
  gap: 24px;
  padding: clamp(28px, 5vw, 56px) clamp(20px, 4vw, 44px);
}
.empty-copy {
  width: 100%;
  max-width: 640px;
}
.empty-copy h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(20px, 2.4vw, 24px);
  font-weight: 600;
  letter-spacing: -0.01em;
}
.empty-copy p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.7;
}
.suggestion-grid {
  display: flex;
  width: 100%;
  max-width: 640px;
  flex-direction: column;
  border-top: 1px solid var(--border);
}
.suggestion-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 11px 4px;
  border: 0;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
  color: var(--text-secondary);
  background: transparent;
  font-family: inherit;
  font-size: var(--fs-sm);
  text-align: left;
  cursor: pointer;
}
.suggestion-card:hover {
  color: var(--text);
  background: var(--surface-hover);
}
.suggestion-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.suggestion-index {
  flex: 0 0 22px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.suggestion-arrow {
  margin-left: auto;
  color: var(--text-muted);
}
.message p {
  margin: 0;
  font-size: var(--fs-md);
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
  margin: 0 0 14px;
  padding: 5px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  font-size: var(--fs-xs);
  line-height: 1.2;
}
.tool-status span {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: tool-pulse 1.4s ease-in-out infinite;
}
@keyframes tool-pulse {
  0%,
  100% {
    opacity: 0.4;
  }
  50% {
    opacity: 1;
  }
}
.confirmation-panel {
  width: 100%;
  margin: 13px auto 0;
  padding: 10px 14px;
  border-color: var(--border-strong);
}
/* 标题与按钮同一行：需要操作时按钮就在眼前，不用往下找 */
.confirmation-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.confirmation-badge {
  flex: 0 0 auto;
  padding: 2px 7px;
  border: 1px solid rgba(201, 162, 95, 0.4);
  border-radius: var(--radius-sm);
  color: var(--warning);
  font-size: var(--fs-xs);
  font-weight: 500;
}
.confirmation-head strong {
  min-width: 0;
  flex: 1;
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 500;
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
  border-radius: var(--radius-sm);
  background: var(--surface);
}
.op-tag {
  flex: 0 0 auto;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  color: var(--warning);
  background: rgba(201, 162, 95, 0.12);
  font-size: var(--fs-xs);
  font-weight: 500;
}
.confirmation-detail {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 10px;
}
/* 参数明细：标题一行，键值对换行排在下面，避免长值把标题挤走 */
.confirmation-facts {
  display: flex;
  width: 100%;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 0;
}
.confirmation-facts div {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.confirmation-facts dt,
.confirmation-facts dd {
  margin: 0;
  font-size: var(--fs-xs);
}
.confirmation-facts dt {
  color: var(--text-muted);
}
.confirmation-facts dd {
  color: var(--text-secondary);
}
.confirmation-detail strong {
  color: var(--text);
  font-size: var(--fs-xs);
  font-weight: 500;
}
.confirmation-detail code {
  min-width: 0;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  word-break: break-all;
}
.confirmation-detail small {
  width: 100%;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.composer {
  /* 固定在整列最底部：不是 sticky，而是 flex 布局里排在消息区之后的一层。
     宽度交给整列（.agent-main）统一决定，自己不再封顶，才能和对话卡片同宽。 */
  position: relative;
  flex: 0 0 auto;
  width: 100%;
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
}
/* 聚焦时只换边框色，不加外发光 */
.composer:focus-within {
  border-color: var(--accent);
}
.composer :deep(.el-textarea__inner) {
  min-height: 56px !important;
  padding: 16px 62px 16px 16px;
  border: none;
  background: transparent;
  box-shadow: none;
  font-size: var(--fs-md);
  line-height: 1.7;
}
/* 发送按钮贴在输入框右下角内侧，并相对输入框垂直居中：
   输入框相对 .composer 内缩 14px（表单 padding），输入框高 56px、按钮 40px，
   上下留白各 8px ⇒ right = 14 + 10 = 24、bottom = 14 + 8 = 22。
   原来写 right/bottom: 10px 是挂在表单边框上的，实测按钮超出输入框右边 4px、
   底边 2px、垂直中心低 10px，看起来就是「位置不对」。 */
.send-button {
  position: absolute;
  right: 24px;
  bottom: 22px;
  width: 40px;
  min-width: 40px;
  height: 40px;
  padding: 0;
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs);
}
.composer-busy {
  margin: 6px 2px 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.4;
}
.composer-foot {
  display: flex;
  flex: 0 0 auto;
  width: 100%;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 4px 12px;
  margin-top: 8px;
}
.assistant-notice,
.composer-hint {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
}
.composer-hint {
  opacity: 0.9;
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
