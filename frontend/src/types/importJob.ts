export type ImportJobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface JamendoImportRequest {
  limit: number
  batch_size: number
}

export interface ImportJobResponse {
  id: number
  source: string
  status: ImportJobStatus
  requested_limit: number
  batch_size: number
  fetched: number
  created: number
  updated: number
  skipped: number
  failure_reasons: Record<string, number>
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}
