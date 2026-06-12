import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface SwotData {
  swot_analysis: Record<string, {
    strengths?: string[]
    weaknesses?: string[]
    opportunities?: string[]
    threats?: string[]
    summary?: string
  }>
}

const DIMENSION_CONFIG = [
  { key: 'strengths', label: '优势', color: 'bg-green-100 text-green-800' },
  { key: 'weaknesses', label: '劣势', color: 'bg-red-100 text-red-800' },
  { key: 'opportunities', label: '机会', color: 'bg-blue-100 text-blue-800' },
  { key: 'threats', label: '威胁', color: 'bg-yellow-100 text-yellow-800' },
] as const

export function SwotSummary({ swot_analysis }: SwotData) {
  const competitors = Object.entries(swot_analysis)

  if (competitors.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">SWOT 分析概览</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {competitors.map(([name, swot]) => (
            <div key={name} className="border rounded-lg p-4">
              <h4 className="font-medium mb-3">{name}</h4>
              {swot.summary && (
                <p className="text-sm text-muted-foreground mb-3">{swot.summary}</p>
              )}
              <div className="grid grid-cols-2 gap-3">
                {DIMENSION_CONFIG.map(({ key, label, color }) => {
                  const items = swot[key] || []
                  if (items.length === 0) return null
                  return (
                    <div key={key}>
                      <Badge className={`${color} mb-2`}>{label}</Badge>
                      <ul className="text-xs space-y-1">
                        {items.slice(0, 3).map((item, i) => (
                          <li key={i} className="text-muted-foreground line-clamp-2">
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
