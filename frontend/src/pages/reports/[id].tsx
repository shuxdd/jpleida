import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft, Download, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import { reportApi } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { FeatureRadar } from '@/components/charts/FeatureRadar'
import { FeatureTable } from '@/components/charts/FeatureTable'
import { PricingBar } from '@/components/charts/PricingBar'
import { SwotSummary } from '@/components/charts/SwotSummary'
import { EvaluationScore } from '@/components/charts/EvaluationScore'

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: reportData, isLoading } = useQuery({
    queryKey: ['report', id],
    queryFn: () => reportApi.get(id!),
    enabled: !!id,
  })

  const { data: chartData } = useQuery({
    queryKey: ['report-chart-data', id],
    queryFn: () => reportApi.getChartData(id!),
    enabled: !!id,
  })

  const { data: evalData } = useQuery({
    queryKey: ['report-evaluation', id],
    queryFn: () => reportApi.getEvaluation(id!),
    enabled: !!id,
  })

  const report = reportData?.data?.data
  const charts = chartData?.data?.data
  const evaluation = evalData?.data?.data

  const handleExport = async () => {
    try {
      const response = await reportApi.export(id!)
      const blob = response.data as Blob
      const url = window.URL.createObjectURL(blob)

      // 从 Content-Disposition 提取文件名
      let filename = `${report?.title || 'report'}.md`
      const disposition = response.headers?.['content-disposition']
      if (disposition) {
        const match = disposition.match(/filename\*?=UTF-8''(.+?)(?:;|$)/)
        if (match) filename = decodeURIComponent(match[1])
      }

      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch {
      // Error toast handled by axios interceptor
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <FileText className="h-12 w-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">报告不存在</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/reports')}>
          返回列表
        </Button>
      </div>
    )
  }

  const hasCharts = charts && (
    (charts.feature_matrix?.features?.length ?? 0) > 0 ||
    Object.keys(charts.pricing_comparison?.competitors ?? {}).length > 0 ||
    Object.keys(charts.swot_analysis ?? {}).length > 0
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/reports')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{report.title}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline">{report.report_type}</Badge>
              <span className="text-sm text-muted-foreground">
                {report.created_at ? formatDate(report.created_at) : ''}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-1" />
            下载报告
          </Button>
        </div>
      </div>

      {/* Tabs: Visualization + Content */}
      <Tabs defaultValue={hasCharts ? 'visualization' : 'content'}>
        <TabsList>
          <TabsTrigger value="visualization" disabled={!hasCharts}>
            数据可视化
          </TabsTrigger>
          <TabsTrigger value="content">报告内容</TabsTrigger>
        </TabsList>

        <TabsContent value="visualization" className="space-y-4 mt-4">
          {charts && <>
            <div className="grid gap-4 md:grid-cols-2">
              {charts.feature_matrix?.features?.length > 0 && (
                <FeatureRadar
                  features={charts.feature_matrix.features}
                  competitors={charts.feature_matrix.competitors}
                />
              )}
              {Object.keys(charts.pricing_comparison?.competitors ?? {}).length > 0 && (
                <PricingBar competitors={charts.pricing_comparison.competitors} />
              )}
            </div>
            {charts.feature_matrix?.features?.length > 0 && (
              <FeatureTable
                features={charts.feature_matrix.features}
                competitors={charts.feature_matrix.competitors}
              />
            )}
            {Object.keys(charts.swot_analysis ?? {}).length > 0 && (
              <SwotSummary swot_analysis={charts.swot_analysis} />
            )}
          </>}
        </TabsContent>

        <TabsContent value="content" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <article className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {report.content}
                </ReactMarkdown>
              </article>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* LLM-as-Judge 评估 */}
      {evaluation && (
        <EvaluationScore evaluation={evaluation} />
      )}
    </div>
  )
}
