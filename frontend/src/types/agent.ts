// Agent SSE 事件与请求参数的共享类型。
export interface AgentEvent {
  type: string
  content: string
}

export interface StreamAgentChatOptions {
  message: string
  sessionId: number | null
  onEvent: (event: AgentEvent) => void
  signal?: AbortSignal
}

/** 待用户确认的高风险工具调用（来自 confirmation_required 事件）。 */
export interface PendingToolConfirmation {
  confirmationId: number
  name: string
  operation: string
  arguments: Record<string, unknown>
  reason: string
}

/** 用户对单条待确认调用的决定。 */
export interface ToolConfirmationDecision {
  confirmationId: number
  approved: boolean
}

export interface StreamToolConfirmationOptions {
  sessionId: number
  decisions: ToolConfirmationDecision[]
  onEvent: (event: AgentEvent) => void
  signal?: AbortSignal
}

/** 历史会话列表项。 */
export interface AgentSessionSummary {
  id: number
  created_at: string
  message_count: number
  /** 会话标题（第一条用户消息）；新建还没说话的会话为 null。 */
  title: string | null
  last_message_id: number | null
}

/** 历史会话里的一条消息。 */
export interface AgentSessionMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/** 单个历史会话的完整内容。 */
export interface AgentSessionDetail {
  id: number
  created_at: string
  messages: AgentSessionMessage[]
}
