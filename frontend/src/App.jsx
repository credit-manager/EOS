import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import arEG from 'antd/locale/ar_EG'
import { useTranslation } from 'react-i18next'

// Pages
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import IndustriesPage from './pages/IndustriesPage'
import BuilderPage from './pages/BuilderPage'
import EntitiesPage from './pages/EntitiesPage'
import ReportsPage from './pages/ReportsPage'
import SettingsPage from './pages/SettingsPage'

// Components
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function AppContent() {
  const { i18n } = useTranslation()
  const locale = i18n.language === 'ar' ? arEG : enUS
  const direction = i18n.language === 'ar' ? 'rtl' : 'ltr'

  React.useEffect(() => {
    document.documentElement.dir = direction
    document.documentElement.lang = i18n.language
  }, [i18n.language, direction])

  return (
    <ConfigProvider locale={locale} theme={{
      token: {
        colorPrimary: '#1890ff',
        borderRadius: 6,
        fontFamily: i18n.language === 'ar' ? "'Cairo', sans-serif" : "'Inter', sans-serif",
      },
    }}>
      <BrowserRouter basename="/ui">
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="industries" element={<IndustriesPage />} />
            <Route path="builder" element={<BuilderPage />} />
            <Route path="entities" element={<EntitiesPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}

export default App
