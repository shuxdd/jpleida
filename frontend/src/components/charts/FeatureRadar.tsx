import { useMemo } from 'react'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface FeatureRadarProps {
  features: string[]
  competitors: Record<string, Record<string, boolean>>
}

const COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6']

export function FeatureRadar({ features, competitors }: FeatureRadarProps) {
  const data = useMemo(() => {
    return features.map((feature) => {
      const row: Record<string, string | number> = { feature }
      for (const [name, featureMap] of Object.entries(competitors)) {
        row[name] = featureMap[feature] ? 1 : 0
      }
      return row
    })
  }, [features, competitors])

  const competitorNames = Object.keys(competitors)

  if (features.length === 0 || competitorNames.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">功能覆盖雷达图</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <RadarChart data={data}>
            <PolarGrid />
            <PolarAngleAxis dataKey="feature" tick={{ fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 1]} tick={false} />
            {competitorNames.map((name, i) => (
              <Radar
                key={name}
                name={name}
                dataKey={name}
                stroke={COLORS[i % COLORS.length]}
                fill={COLORS[i % COLORS.length]}
                fillOpacity={0.15}
              />
            ))}
            <Legend />
            <Tooltip />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
