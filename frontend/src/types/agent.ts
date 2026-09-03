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
