import axios from 'axios'
import { ElMessage } from 'element-plus'

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>
}

export function showError(error: unknown, fallback = '请求失败，请稍后重试'): void {
  let message = fallback
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') message = detail
    else if (Array.isArray(detail)) message = detail[0]?.msg ?? fallback
    else if (error.code === 'ECONNABORTED') message = '请求超时，请检查网络后重试'
    else if (!error.response) message = '无法连接服务，请确认后端已启动'
  }
  ElMessage.closeAll()
  ElMessage({ message, type: 'error', duration: 2600, grouping: true, showClose: true })
}

export function showSuccess(message: string): void {
  ElMessage.closeAll()
  ElMessage({ message, type: 'success', duration: 1800, grouping: true })
}
