import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check, X } from 'lucide-react'

interface FeatureTableProps {
  features: string[]
  competitors: Record<string, Record<string, boolean>>
}

export function FeatureTable({ features, competitors }: FeatureTableProps) {
  const competitorNames = Object.keys(competitors)

  if (features.length === 0 || competitorNames.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">功能矩阵</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3 font-medium">功能</th>
                {competitorNames.map((name) => (
                  <th key={name} className="text-center py-2 px-3 font-medium">
                    {name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {features.map((feature) => (
                <tr key={feature} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="py-2 px-3">{feature}</td>
                  {competitorNames.map((name) => (
                    <td key={name} className="text-center py-2 px-3">
                      {competitors[name][feature] ? (
                        <Check className="h-4 w-4 text-green-500 mx-auto" />
                      ) : (
                        <X className="h-4 w-4 text-muted-foreground/30 mx-auto" />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Check className="h-3 w-3 text-green-500" />
            支持
          </div>
          <div className="flex items-center gap-1">
            <X className="h-3 w-3 text-muted-foreground/30" />
            不支持
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
