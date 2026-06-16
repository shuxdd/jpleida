import { useState, useRef, useEffect, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Send,
  Bot,
  User,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Check,
  Loader2,
  MessageSquare,
  Plus,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { qaApi } from '@/lib/api'
import { toast } from 'sonner'
import type { ChatSession, ChatMessage, QAResponse, SourceItem } from '@/types'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceItem[]
  timestamp: Date
}

const SOURCE_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  knowledge_base: { label: '知识库', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  report: { label: '报告', color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
  analysis: { label: '分析', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' },
}

export default function QA() {
  const queryClient = useQueryClient()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 会话列表
  const { data: sessionsData, isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: async () => {
      const res = await qaApi.listSessions()
      return res.data.data as ChatSession[]
    },
  })
  const sessions = sessionsData || []

  // 加载消息
  const loadMessages = useCallback(async (sessionId: string) => {
    try {
      const res = await qaApi.listMessages(sessionId)
      const msgs = res.data.data as ChatMessage[]
      setMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources,
          timestamp: m.created_at ? new Date(m.created_at) : new Date(),
        }))
      )
    } catch {
      setMessages([])
    }
  }, [])

  // 切换会话
  const handleSelectSession = async (session: ChatSession) => {
    setActiveSessionId(session.id)
    await loadMessages(session.id)
  }

  // 创建会话
  const createMutation = useMutation({
    mutationFn: () => qaApi.createSession(),
    onSuccess: (res) => {
      const session = res.data.data as ChatSession
      setActiveSessionId(session.id)
      setMessages([])
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setTimeout(() => inputRef.current?.focus(), 100)
    },
  })

  // 删除会话
  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => qaApi.deleteSession(sessionId),
    onSuccess: () => {
      setActiveSessionId(null)
      setMessages([])
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
    },
  })

  // 问答
  const qaMutation = useMutation({
    mutationFn: ({ sessionId, question }: { sessionId: string; question: string }) =>
      qaApi.askInSession(sessionId, { question }),
    onSuccess: (response) => {
      const { answer, sources } = response.data.data as QAResponse

      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: answer,
        sources,
        timestamp: new Date(),
      }

      // 打字机效果
      setIsTyping(true)
      let currentText = ''
      const chars = answer.split('')
      let index = 0

      const typeInterval = setInterval(() => {
        if (index < chars.length) {
          currentText += chars[index]
          setMessages((prev) => {
            const newMessages = [...prev]
            const lastMessage = newMessages[newMessages.length - 1]
            if (lastMessage.role === 'assistant') {
              lastMessage.content = currentText
            }
            return newMessages
          })
          index++
        } else {
          clearInterval(typeInterval)
          setIsTyping(false)
        }
      }, 20)

      setMessages((prev) => [...prev, assistantMessage])
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
    },
    onError: (error: Error) => {
      toast.error(error.message)
      setIsTyping(false)
    },
  })

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || qaMutation.isPending) return

    // 自动创建会话
    let sessionId = activeSessionId
    if (!sessionId) {
      try {
        const res = await qaApi.createSession()
        const session = res.data.data as ChatSession
        sessionId = session.id
        setActiveSessionId(session.id)
        queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      } catch {
        toast.error('创建会话失败')
        return
      }
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    qaMutation.mutate({ sessionId, question })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCopy = (content: string, id: string) => {
    navigator.clipboard.writeText(content)
    setCopiedId(id)
    toast.success('已复制到剪贴板')
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleNewChat = () => {
    createMutation.mutate()
  }

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    deleteMutation.mutate(sessionId)
  }

  const sourceTypeBadge = (source: SourceItem) => {
    const info = SOURCE_TYPE_LABELS[source.type] || { label: source.type, color: 'bg-gray-100 text-gray-700' }
    return (
      <Badge key={`${source.type}-${source.competitor}-${source.title}`} className={`${info.color} border-0 text-xs`}>
        {source.competitor ? `${source.competitor} · ${info.label}` : info.label}
      </Badge>
    )
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Sidebar */}
      <Card className="w-64 flex-shrink-0 hidden lg:flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">对话历史</CardTitle>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleNewChat}
              disabled={createMutation.isPending}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto scrollbar-thin">
          {sessionsLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">暂无对话记录</p>
          ) : (
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group flex items-center gap-2 p-2 rounded-md cursor-pointer text-sm transition-colors ${
                    activeSessionId === session.id
                      ? 'bg-accent text-accent-foreground'
                      : 'hover:bg-accent/50'
                  }`}
                  onClick={() => handleSelectSession(session)}
                >
                  <MessageSquare className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate">{session.title}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 flex-shrink-0"
                    onClick={(e) => handleDeleteSession(e, session.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Chat Area */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="pb-3 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div>
                <CardTitle className="text-base">智能问答助手</CardTitle>
                <p className="text-xs text-muted-foreground">
                  基于竞品知识库、报告和分析结果的智能问答
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {sessions.length > 0 && (
                <select
                  className="hidden sm:flex h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                  value={activeSessionId || ''}
                  onChange={(e) => {
                    const s = sessions.find((s) => s.id === e.target.value)
                    if (s) handleSelectSession(s)
                  }}
                >
                  <option value="" disabled>切换会话</option>
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
              )}
              <Button variant="outline" size="sm" onClick={handleNewChat} disabled={createMutation.isPending}>
                <Plus className="h-4 w-4 mr-1" />
                新对话
              </Button>
            </div>
          </div>
        </CardHeader>

        {/* Messages */}
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Bot className="h-8 w-8 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">有什么可以帮您的？</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                我可以基于您的竞品知识库、已有报告和分析结果回答问题。支持连续对话。
              </p>
              <div className="grid grid-cols-2 gap-2 mt-6 max-w-md w-full">
                {[
                  '竞品A的核心优势是什么？',
                  '我们的定价策略如何？',
                  '市场上有哪些新趋势？',
                  '如何提升产品竞争力？',
                ].map((question) => (
                  <Button
                    key={question}
                    variant="outline"
                    className="text-left h-auto py-2 px-3 text-sm"
                    onClick={() => setInput(question)}
                  >
                    {question}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    } rounded-lg p-3`}
                  >
                    {message.role === 'assistant' ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    )}

                        {/* 结构化来源 */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t space-y-2">
                        <p className="text-xs text-muted-foreground">参考来源：</p>
                        <div className="flex flex-wrap gap-1">
                          {message.sources.map((source, idx) => (
                            <span
                              key={idx}
                              className="group relative"
                            >
                              {sourceTypeBadge(source)}
                              <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-10">
                                <div className="bg-popover text-popover-foreground rounded-md shadow-md border px-3 py-2 text-xs max-w-[260px]">
                                  <p className="font-medium mb-1">
                                    {source.type === 'knowledge_base' && '📄 知识库'}
                                    {source.type === 'report' && '📊 报告'}
                                    {source.type === 'analysis' && '🔍 分析结果'}
                                  </p>
                                  {source.competitor && (
                                    <p className="text-muted-foreground">竞品: {source.competitor}</p>
                                  )}
                                  {source.title && (
                                    <p className="text-muted-foreground truncate">{source.title}</p>
                                  )}
                                  {source.snippet && (
                                    <p className="text-muted-foreground mt-1 border-t pt-1">{
                                      source.snippet.length > 100
                                        ? source.snippet.slice(0, 100) + '...'
                                        : source.snippet
                                    }</p>
                                  )}
                                </div>
                              </div>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {message.role === 'assistant' && (
                      <div className="flex items-center gap-1 mt-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleCopy(message.content, message.id)}
                        >
                          {copiedId === message.id ? (
                            <Check className="h-3 w-3" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7">
                          <ThumbsUp className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7">
                          <ThumbsDown className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </div>

                  {message.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}

              {qaMutation.isPending && !isTyping && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="bg-muted rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">正在思考...</span>
                    </div>
                  </div>
                </div>
              )}

              {isTyping && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="bg-muted rounded-lg p-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" />
                      <div
                        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                        style={{ animationDelay: '0.1s' }}
                      />
                      <div
                        className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                        style={{ animationDelay: '0.2s' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </CardContent>

        {/* Input */}
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              placeholder={activeSessionId ? '输入您的问题...' : '输入问题开始新对话...'}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={qaMutation.isPending}
              className="flex-1"
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || qaMutation.isPending}
            >
              {qaMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            按 Enter 发送，Shift + Enter 换行。支持连续追问。
          </p>
        </div>
      </Card>
    </div>
  )
}
