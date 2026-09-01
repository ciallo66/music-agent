import { http } from './http'
import type { ImportJobResponse, JamendoImportRequest } from '../types/importJob'

export function createJamendoImport(payload: JamendoImportRequest) {
  return http.post<ImportJobResponse>('/admin/imports/jamendo', payload)
}

export function listImportJobs(limit = 20) {
  return http.get<ImportJobResponse[]>('/admin/imports', { params: { limit } })
}
