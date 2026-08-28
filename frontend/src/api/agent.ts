import { getAccessToken, refreshAccessToken } from './http'

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

/** 发送 Agent SSE 请求，统一处理认证刷新和事件解析。 */
export async function streamAgentChat(options: StreamAgentChatOptions): Promise<number | null> {
  let token = getAccessToken()
  let response = await request(options, token)
  if (response.status === 401) {
    token = await refreshAccessToken()
    response = await request(options, token)
  }
  if (!response.ok || response.body === null) throw new Error('Agent 请求失败')

  const sessionIdHeader = response.headers.get('X-Session-Id')
  const returnedSessionId = sessionIdHeader === null ? null : Number(sessionIdHeader)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
      const chunks = buffer.split(/\r?\n\r?\n/)
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) emitChunk(chunk, options.onEvent)
      if (done) {
        if (buffer.trim()) emitChunk(buffer, options.onEvent)
        break
      }
    }
  } finally {
    reader.releaseLock()
  }
  return Number.isInteger(returnedSessionId) ? returnedSessionId : null
}

async function request(options: StreamAgentChatOptions, token: string | null): Promise<Response> {
  return fetch('/api/v1/agent/chat', {
    method: 'POST',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token === null ? {} : { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify({ message: options.message, session_id: options.sessionId }),
  })
}

function emitChunk(chunk: string, onEvent: (event: AgentEvent) => void): void {
  const dataLine = chunk.split(/\r?\n/).find((line) => line.startsWith('data:'))
  if (!dataLine) return
  const eventLine = chunk.split(/\r?\n/).find((line) => line.startsWith('event:'))
  const payload = JSON.parse(dataLine.slice(5).trim()) as Partial<AgentEvent>
  const event: AgentEvent = {
    type: eventLine?.slice(6).trim() || payload.type || 'message',
    content: typeof payload.content === 'string' ? payload.content : '',
  }
  onEvent(event)
}
