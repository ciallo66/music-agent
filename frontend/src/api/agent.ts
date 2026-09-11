// Agent SSE 通信：处理鉴权刷新、事件拆包与类型收窄。
import { getAccessToken, refreshAccessToken } from './http'
import type {
  AgentEvent,
  PendingToolConfirmation,
  StreamAgentChatOptions,
  StreamToolConfirmationOptions,
} from '../types/agent'
export type {
  AgentEvent,
  StreamAgentChatOptions,
  StreamToolConfirmationOptions,
} from '../types/agent'

/** 发送 Agent 对话请求，统一处理认证刷新和事件解析。 */
export async function streamAgentChat(options: StreamAgentChatOptions): Promise<number | null> {
  return streamRequest(
    '/api/v1/agent/chat',
    { message: options.message, session_id: options.sessionId },
    options.onEvent,
    options.signal,
  )
}

/** 提交待确认工具调用的处理结果，并继续消费同一条 Agent 流。 */
export async function streamToolConfirmations(
  options: StreamToolConfirmationOptions,
): Promise<number | null> {
  return streamRequest(
    '/api/v1/agent/confirmations',
    {
      session_id: options.sessionId,
      decisions: options.decisions.map((decision) => ({
        confirmation_id: decision.confirmationId,
        approved: decision.approved,
      })),
    },
    options.onEvent,
    options.signal,
  )
}

/** 解析 confirmation_required 事件负载；负载异常时返回 null。 */
export function parseToolConfirmation(content: string): PendingToolConfirmation | null {
  try {
    const payload = JSON.parse(content) as Record<string, unknown>
    const confirmationId = Number(payload.confirmation_id)
    if (!Number.isInteger(confirmationId) || confirmationId <= 0) return null
    const rawArguments = payload.arguments
    return {
      confirmationId,
      name: typeof payload.name === 'string' ? payload.name : '未知工具',
      operation: typeof payload.operation === 'string' ? payload.operation : '',
      arguments:
        typeof rawArguments === 'object' && rawArguments !== null
          ? (rawArguments as Record<string, unknown>)
          : {},
      reason: typeof payload.reason === 'string' ? payload.reason : '',
    }
  } catch {
    return null
  }
}

// 发起一次带认证信息的 Agent SSE 请求。
async function request(
  path: string,
  body: unknown,
  token: string | null,
  signal?: AbortSignal,
): Promise<Response> {
  return fetch(path, {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token === null ? {} : { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(body),
  })
}

// 共用的流式读取：401 时刷新一次令牌并重试，然后逐块拆包交给调用方。
async function streamRequest(
  path: string,
  body: unknown,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<number | null> {
  let token = getAccessToken()
  let response = await request(path, body, token, signal)
  if (response.status === 401) {
    token = await refreshAccessToken()
    response = await request(path, body, token, signal)
  }
  if (!response.ok || response.body === null) throw new Error(await readErrorMessage(response))

  const sessionIdHeader = response.headers.get('X-Session-Id')
  const returnedSessionId = sessionIdHeader === null ? null : Number(sessionIdHeader)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
      // SSE 事件以空行分隔；保留最后一个不完整片段，防止跨网络包截断 JSON。
      const chunks = buffer.split(/\r?\n\r?\n/)
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) emitChunk(chunk, onEvent)
      if (done) {
        if (buffer.trim()) emitChunk(buffer, onEvent)
        break
      }
    }
  } finally {
    reader.releaseLock()
  }
  return Number.isInteger(returnedSessionId) ? returnedSessionId : null
}

// 取出后端返回的 detail，让前端能显示"已被处理或已过期"这类具体原因。
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === 'string' && payload.detail.length > 0) return payload.detail
  } catch {
    // 响应不是 JSON 时退回默认文案。
  }
  return 'Agent 请求失败'
}

// 解析单个 SSE 事件块，并将未知字段收窄为前端事件类型。
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
