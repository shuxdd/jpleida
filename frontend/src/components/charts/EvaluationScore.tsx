import type { EvaluationResult } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

interface Props {
  evaluation: EvaluationResult
}

const DIMENSIONS = [
  { key: 'coverage' as const, label: '覆盖度', desc: '竞品和维度的覆盖程度' },
  { key: 'depth' as const, label: '分析深度', desc: '分析的具体性和数据支撑' },
  { key: 'structure' as const, label: '结构化', desc: '报告结构的清晰度和规范性' },
  { key: 'actionability' as const, label: '可操作性', desc: '战略建议的执行性' },
]

function ScoreBar({ score, label, desc, reasoning }: {
  score: number
  label: string
  desc: string
  reasoning: string
}) {
  const pct = (score / 5) * 100
  const color =
    score >= 4 ? 'bg-green-500' :
    score >= 3 ? 'bg-amber-500' :
    'bg-red-500'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <div>
          <span className="font-medium">{label}</span>
          <span className="text-muted-foreground ml-2">{desc}</span>
        </div>
        <span className="font-mono tabular-nums">{score}/5</span>
      </div>
      <Progress value={pct} className={`h-2 ${color}`} />
      {reasoning && (
        <p className="text-xs text-muted-foreground">{reasoning}</p>
      )}
    </div>
  )
}

export function EvaluationScore({ evaluation }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          报告质量评估
          <span className="text-xs text-muted-foreground font-normal">
            LLM-as-Judge 自动评分
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {DIMENSIONS.map(({ key, label, desc }) => (
          <ScoreBar
            key={key}
            score={evaluation[key].score}
            label={label}
            desc={desc}
            reasoning={evaluation[key].reasoning}
          />
        ))}

        <div className="border-t pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold text-sm">总体评分</span>
            <span className={`font-mono font-bold tabular-nums ${
              evaluation.overall_score >= 4 ? 'text-green-600' :
              evaluation.overall_score >= 3 ? 'text-amber-600' :
              'text-red-600'
            }`}>
              {evaluation.overall_score.toFixed(1)}/5
            </span>
          </div>
          {evaluation.overall_summary && (
            <p className="text-sm text-muted-foreground">{evaluation.overall_summary}</p>
          )}
        </div>

        {evaluation.key_improvements.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="text-sm font-semibold mb-2">改进建议</h4>
            <ul className="space-y-1">
              {evaluation.key_improvements.map((item, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5 shrink-0">{i + 1}.</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {evaluation.diagnosis.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="text-sm font-semibold mb-2">节点诊断</h4>
            <ul className="space-y-1">
              {evaluation.diagnosis.map((item, i) => (
                <li key={i} className="text-xs font-mono text-muted-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
