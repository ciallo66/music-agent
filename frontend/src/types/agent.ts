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
