import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, useRef } from 'react'
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FileText,
  Search,
  Globe,
  BarChart3,
  FileEdit,
  Cpu,
  Database,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { analysisApi, reportApi } from '@/lib/api'
import { formatDate } from '@/lib/utils'

const dimensionLabels: Record<string, string> = {
  features: '功能特性',
  pricing: '定价策略',
  swot: 'SWOT 分析',
  marketing: '营销策略',
}

interface ProgressUpdate {
  node: string
  progress: number
  message: string
}

const nodeLabels: Record<string, { label: string; icon: React.ReactNode }> = {
  planner: { label: '任务规划', icon: <Cpu className="h-4 w-4" /> },
  searcher: { label: '数据采集', icon: <Search className="h-4 w-4" /> },
  scraper: { label: '网页爬取', icon: <Globe className="h-4 w-4" /> },
  extractor: { label: '信息提取', icon: <Database className="h-4 w-4" /> },
  analyzer: { label: '对比分析', icon: <BarChart3 className="h-4 w-4" /> },
  reporter: { label: '报告生成', icon: <FileEdit className="h-4 w-4" /> },
}

const nodeOrder = ['planner', 'searcher', 'scraper', 'extractor', 'analyzer', 'reporter']

export default function AnalysisDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const [progressUpdates, setProgressUpdates] = useState<ProgressUpdate[]>([])
  const [currentProgress, setCurrentProgress] = useState(0)
  const [currentMessage, setCurrentMessage] = useState('')

  const { data, error } = useQuery({
    queryKey: ['analysis-task', id],
    queryFn: () => analysisApi.getTask(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.data?.data?.status
      if (status && status !== 'completed' && status !== 'failed') return 3000
      return false
    },
    retry: 3,
    retryDelay: 2000,
  })

  const task = data?.data?.data

  // WebSocket 连接
  useEffect(() => {
    if (!id || !task) return
    if (task.status !== 'running' && task.status !== 'pending' && task.status !== 'collecting' && task.status !== 'planning') return

    const token = localStorage.getItem('auth_token')
    const apiUrl = import.meta.env.VITE_API_URL || ''
    const wsUrl = apiUrl
      ? `${apiUrl.replace('http', 'ws')}/ws/analysis/${id}?token=${token}`
      : `/ws/analysis/${id}?token=${token}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[WS] 已连接:', id)
    }

    ws.onmessage = (event) => {
      try {
        const update: ProgressUpdate = JSON.parse(event.data)
        setProgressUpdates((prev) => {
          // 去重：同一节点只保留最新
          const filtered = prev.filter((u) => u.node !== update.node)
          return [...filtered, update].sort(
            (a, b) => nodeOrder.indexOf(a.node) - nodeOrder.indexOf(b.node)
          )
        })
        setCurrentProgress(update.progress)
        setCurrentMessage(update.message)
      } catch (e) {
        console.warn('[WS] 解析失败:', e)
      }
    }

    ws.onclose = () => {
      console.log('[WS] 已断开')
    }

    ws.onerror = (e) => {
      console.warn('[WS] 错误:', e)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [id, task?.status])

  // 任务完成时断开 WS
  useEffect(() => {
    if (task?.status === 'completed' || task?.status === 'failed') {
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [task?.status])

  const taskStatus = task?.status

  // 任务完成时查询关联报告
  const { data: reportData } = useQuery({
    queryKey: ['task-report', id],
    queryFn: () => reportApi.list({ analysis_id: id, page_size: 1 }),
    enabled: !!id && taskStatus === 'completed',
  })

  const reportId = reportData?.data?.data?.[0]?.id

  // 任务完成时刷新报告列表
  useEffect(() => {
    if (taskStatus === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    }
  }, [taskStatus, queryClient])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-muted-foreground" />
      case 'running':
      case 'planning':
      case 'collecting':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning'> = {
      pending: 'secondary',
      running: 'warning',
      planning: 'warning',
      collecting: 'warning',
      completed: 'success',
      failed: 'destructive',
    }
    const labels: Record<string, string> = {
      pending: '待执行',
      running: '执行中',
      planning: '规划中',
      collecting: '采集中',
      completed: '已完成',
      failed: '失败',
    }
    return (
      <Badge variant={variants[status] || 'default'} className="text-sm">
        {labels[status] || status}
      </Badge>
    )
  }

  // 判断是否在执行中
  const isRunning = task && ['pending', 'running', 'planning', 'collecting'].includes(task.status)

  if (!task) {
    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-20">
          <FileText className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">{error.message?.includes('404') ? '任务不存在' : '加载失败，请稍后重试'}</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/analysis')}>
            返回列表
          </Button>
        </div>
      )
    }
    // 仍在加载中
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  // 轮询失败时保留上次数据，不跳错误页
  if (error) {
    console.warn('[Analysis] 轮询失败，使用缓存数据:', error)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/analysis')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">分析任务详情</h1>
          <p className="text-sm text-muted-foreground font-mono">{task.id}</p>
        </div>
      </div>

      {/* Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            {getStatusIcon(task.status)}
            任务状态
            {getStatusBadge(task.status)}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-sm text-muted-foreground">创建时间</p>
              <p className="text-sm">{task.created_at ? formatDate(task.created_at) : '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">完成时间</p>
              <p className="text-sm">{task.completed_at ? formatDate(task.completed_at) : '-'}</p>
            </div>
            {task.my_product && (
              <div>
                <p className="text-sm text-muted-foreground">我方产品</p>
                <p className="text-sm">{task.my_product}</p>
              </div>
            )}
          </div>

          {/* Competitors */}
          <div>
            <p className="text-sm text-muted-foreground mb-2">竞品</p>
            <div className="flex gap-2 flex-wrap">
              {task.competitors.map((name) => (
                <Badge key={name} variant="outline">{name}</Badge>
              ))}
            </div>
          </div>

          {/* Dimensions */}
          <div>
            <p className="text-sm text-muted-foreground mb-2">分析维度</p>
            <div className="flex gap-2 flex-wrap">
              {task.dimensions.map((dim) => (
                <Badge key={dim} variant="secondary">
                  {dimensionLabels[dim] || dim}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Running state - 实时进度 */}
      {isRunning && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
              分析进度
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 进度条 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {currentMessage || '准备中...'}
                </span>
                <span className="font-medium text-blue-500">{currentProgress}%</span>
              </div>
              <Progress value={currentProgress} className="h-2" />
            </div>

            {/* 步骤列表 */}
            <div className="space-y-3">
              {nodeOrder.map((nodeKey) => {
                const info = nodeLabels[nodeKey]
                const update = progressUpdates.find((u) => u.node === nodeKey)
                const isDone = !!update
                const isCurrent = update && update.progress < 100 && !progressUpdates.find(
                  (u) => nodeOrder.indexOf(u.node) > nodeOrder.indexOf(nodeKey)
                )

                return (
                  <div
                    key={nodeKey}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                      isCurrent
                        ? 'bg-blue-50 border border-blue-200'
                        : isDone
                        ? 'bg-green-50 border border-green-200'
                        : 'bg-muted/30'
                    }`}
                  >
                    <div
                      className={`flex items-center justify-center w-8 h-8 rounded-full ${
                        isDone && !isCurrent
                          ? 'bg-green-500 text-white'
                          : isCurrent
                          ? 'bg-blue-500 text-white'
                          : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {isDone && !isCurrent ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : (
                        info.icon
                      )}
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${isDone && !isCurrent ? 'text-green-700' : ''}`}>
                        {info.label}
                      </p>
                      {update && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {update.message}
                        </p>
                      )}
                    </div>
                    {isCurrent && (
                      <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                    )}
                    {isDone && !isCurrent && (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    )}
                  </div>
                )
              })}
            </div>

            <p className="text-xs text-muted-foreground text-center">
              WebSocket 实时推送 · 页面会自动刷新
            </p>
          </CardContent>
        </Card>
      )}

      {/* Failed state */}
      {task.status === 'failed' && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <XCircle className="h-8 w-8 text-red-500 mb-4" />
            <p className="text-red-500 font-medium">分析失败</p>
            {task.error_message && (
              <p className="text-sm text-muted-foreground mt-2">{task.error_message}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Completed state - show results */}
      {task.status === 'completed' && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <CheckCircle2 className="h-8 w-8 text-green-500 mb-4" />
            <p className="text-green-500 font-medium mb-2">分析完成</p>
            {task.error_message && (
              <p className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded px-4 py-2 mb-4 max-w-md text-center">
                {task.error_message}
              </p>
            )}
            <Button onClick={() => reportId && navigate(`/reports/${reportId}`)}>
              <FileText className="mr-2 h-4 w-4" />
              查看报告
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
