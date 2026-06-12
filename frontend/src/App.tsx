import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { queryClient } from '@/lib/queryClient'
import { MainLayout } from '@/layouts/MainLayout'
import Dashboard from '@/pages/dashboard'
import CompetitorList from '@/pages/competitors'
import AnalysisList from '@/pages/analysis'
import ReportList from '@/pages/reports'
import ReportDetail from '@/pages/reports/[id]'
import QA from '@/pages/qa'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="competitors" element={<CompetitorList />} />
            <Route path="analysis" element={<AnalysisList />} />
            <Route path="reports" element={<ReportList />} />
            <Route path="reports/:id" element={<ReportDetail />} />
            <Route path="qa" element={<QA />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  )
}

export default App
