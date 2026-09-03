// 管理员导入任务的 HTTP 接口封装。
import { http } from './http'
import type { ImportJobResponse, JamendoImportRequest } from '../types/importJob'

// 创建一次 Jamendo 导入任务。
export function createJamendoImport(payload: JamendoImportRequest) {
  return http.post<ImportJobResponse>('/admin/imports/jamendo', payload)
}

// 查询最近导入任务。
export function listImportJobs(limit = 20) {
  return http.get<ImportJobResponse[]>('/admin/imports', { params: { limit } })
}
