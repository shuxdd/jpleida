import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface PricingData {
  competitors: Record<string, {
    prices: Array<{ name: string; price: number; currency: string }>
    min_price?: number
    max_price?: number
    note?: string
  }>
}

const COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6']

export function PricingBar({ competitors }: PricingData) {
  const data = useMemo(() => {
    // 收集所有套餐名
    const allTiers = new Set<string>()
    for (const comp of Object.values(competitors)) {
      for (const p of comp.prices || []) {
        allTiers.add(p.name)
      }
    }

    if (allTiers.size === 0) return []

    return Array.from(allTiers).map((tier) => {
      const row: Record<string, string | number> = { tier }
      for (const [name, comp] of Object.entries(competitors)) {
        const price = comp.prices?.find((p) => p.name === tier)
        row[name] = price?.price ?? 0
      }
      return row
    })
  }, [competitors])

  const competitorNames = Object.keys(competitors)

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">定价对比</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">暂无定价数据</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">定价对比</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tier" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {competitorNames.map((name, i) => (
              <Bar
                key={name}
                dataKey={name}
                fill={COLORS[i % COLORS.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
