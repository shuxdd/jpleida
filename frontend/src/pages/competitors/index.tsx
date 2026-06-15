import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  ExternalLink,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Pagination } from '@/components/ui/pagination'
import { competitorApi } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { toast } from 'sonner'
import type { Competitor, CompetitorCreateRequest } from '@/types'

export default function CompetitorList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [showDialog, setShowDialog] = useState(false)
  const [editingCompetitor, setEditingCompetitor] = useState<Competitor | null>(null)
  const [formData, setFormData] = useState<CompetitorCreateRequest>({
    name: '',
    industry: '',
    tags: [],
    notes: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['competitors', page, keyword],
    queryFn: () => competitorApi.list({ page, page_size: 10, keyword }),
  })

  const createMutation = useMutation({
    mutationFn: (data: CompetitorCreateRequest) => competitorApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      toast.success('创建成功')
      setShowDialog(false)
      resetForm()
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CompetitorCreateRequest }) =>
      competitorApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      toast.success('更新成功')
      setShowDialog(false)
      resetForm()
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => competitorApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      toast.success('删除成功')
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const competitors = data?.data?.data || []
  const total = data?.data?.total || 0
  const totalPages = Math.ceil(total / 10)

  const resetForm = () => {
    setFormData({ name: '', industry: '', tags: [], notes: '' })
    setEditingCompetitor(null)
  }

  const handleCreate = () => {
    resetForm()
    setShowDialog(true)
  }

  const handleEdit = (competitor: Competitor) => {
    setEditingCompetitor(competitor)
    setFormData({
      name: competitor.name,
      industry: competitor.industry || '',
      tags: competitor.tags,
      notes: competitor.notes || '',
    })
    setShowDialog(true)
  }

  const handleDelete = (id: string) => {
    if (confirm('确定要删除这个竞品吗？')) {
      deleteMutation.mutate(id)
    }
  }

  const handleSubmit = () => {
    if (!formData.name.trim()) {
      toast.error('请输入竞品名称')
      return
    }

    if (editingCompetitor) {
      updateMutation.mutate({ id: editingCompetitor.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleTagsChange = (value: string) => {
    const tags = value.split(',').map((t) => t.trim()).filter(Boolean)
    setFormData((prev) => ({ ...prev, tags }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">竞品管理</h1>
          <p className="text-muted-foreground mt-2">管理您的竞品信息</p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          添加竞品
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索竞品名称..."
                value={keyword}
                onChange={(e) => {
                  setKeyword(e.target.value)
                  setPage(1)
                }}
                className="pl-8"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-32 mb-2" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                </div>
              ))}
            </div>
          ) : competitors.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground mb-4">暂无竞品数据</p>
              <Button variant="outline" onClick={handleCreate}>
                <Plus className="mr-2 h-4 w-4" />
                添加第一个竞品
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>行业</TableHead>
                  <TableHead>标签</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="w-[100px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {competitors.map((competitor: Competitor) => (
                  <TableRow key={competitor.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center">
                          <span className="text-sm font-medium text-primary">
                            {competitor.name.charAt(0)}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium">{competitor.name}</p>
                          {competitor.website && (
                            <a
                              href={competitor.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1"
                            >
                              {competitor.website}
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {competitor.industry ? (
                        <Badge variant="outline">{competitor.industry}</Badge>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {competitor.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                        {competitor.tags.length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{competitor.tags.length - 3}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {competitor.created_at ? formatDate(competitor.created_at) : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleEdit(competitor)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => handleDelete(competitor.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="py-4 border-t">
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingCompetitor ? '编辑竞品' : '添加竞品'}
            </DialogTitle>
            <DialogDescription>
              {editingCompetitor
                ? '修改竞品的基本信息'
                : '填写竞品的基本信息来创建新的竞品'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">竞品名称 *</Label>
              <Input
                id="name"
                placeholder="输入竞品名称"
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="industry">行业</Label>
              <Input
                id="industry"
                placeholder="如：电商、社交、SaaS"
                value={formData.industry}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, industry: e.target.value }))
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tags">标签</Label>
              <Input
                id="tags"
                placeholder="多个标签用逗号分隔"
                value={formData.tags.join(', ')}
                onChange={(e) => handleTagsChange(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">竞品信息</Label>
              <Textarea
                id="notes"
                placeholder="可选，填写你了解的额外信息"
                value={formData.notes}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, notes: e.target.value }))
                }
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowDialog(false)
                resetForm()
              }}
            >
              取消
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {editingCompetitor ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
