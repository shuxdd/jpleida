import axios from 'axios'
import type {
  Competitor,
  CompetitorCreateRequest,
  CompetitorUpdateRequest,
  AnalysisTask,
  AnalysisSubmitRequest,
  Report,
  QARequest,
  QAResponse,
  ApiResponse,
  PaginatedResponse,
} from '@/types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器 - 解包 data 字段
api.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse | PaginatedResponse
    if (data.code !== 200) {
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return response
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '网络错误'
    return Promise.reject(new Error(message))
  }
)

// 竞品 API
export const competitorApi = {
  list: (params?: {
    page?: number
    page_size?: number
    keyword?: string
    industry?: string
  }) => api.get<PaginatedResponse<Competitor>>('/api/competitors', { params }),

  get: (id: string) => api.get<ApiResponse<Competitor>>(`/api/competitors/${id}`),

  create: (data: CompetitorCreateRequest) =>
    api.post<ApiResponse<Competitor>>('/api/competitors', data),

  update: (id: string, data: CompetitorUpdateRequest) =>
    api.put<ApiResponse<Competitor>>(`/api/competitors/${id}`, data),

  delete: (id: string) => api.delete<ApiResponse>(`/api/competitors/${id}`),
}

// 分析任务 API
export const analysisApi = {
  submit: (data: AnalysisSubmitRequest) =>
    api.post<ApiResponse<{ task_id: string; status: string }>>('/api/analysis', data),

  getTask: (taskId: string) =>
    api.get<ApiResponse<AnalysisTask>>(`/api/analysis/${taskId}`),

  listTasks: (params?: { page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<AnalysisTask>>('/api/analysis', { params }),
}

// 报告 API
export const reportApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<Report>>('/api/reports', { params }),

  get: (id: string) => api.get<ApiResponse<Report>>(`/api/reports/${id}`),

  getChartData: (id: string) =>
    api.get<ApiResponse<ChartDataResponse>>(`/api/reports/${id}/chart-data`),
}

// 图表数据类型
export interface ChartDataResponse {
  competitors: string[]
  analysis_type: string
  dimensions: string[]
  feature_matrix: {
    features: string[]
    competitors: Record<string, Record<string, boolean>>
  }
  pricing_comparison: {
    competitors: Record<string, {
      prices: Array<{ name: string; price: number; currency: string }>
      min_price?: number
      max_price?: number
      currency?: string
      note?: string
    }>
  }
  swot_analysis: Record<string, {
    strengths?: string[]
    weaknesses?: string[]
    opportunities?: string[]
    threats?: string[]
    summary?: string
  }>
  competitors_data: Record<string, Record<string, unknown>>
}

// 智能问答 API
export const qaApi = {
  ask: (data: QARequest) =>
    api.post<ApiResponse<QAResponse>>('/api/qa', data),
}

export default api
