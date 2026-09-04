import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Card, Col, Empty, Row, Skeleton, Statistic } from 'antd'
import { DollarOutlined, FallOutlined, RiseOutlined, TeamOutlined, ProjectOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { Line, Bar } from '@ant-design/charts'
import api from '../services/api'

function DashboardPage() {
  const { t } = useTranslation()
  const [summary, setSummary] = useState(null)
  const [revenue, setRevenue] = useState([])
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [summaryResponse, revenueResponse, expensesResponse] = await Promise.all([
          api.get('/analytics/executive'),
          api.get('/analytics/revenue-trend', { params: { months: 12 } }),
          api.get('/analytics/expenses-trend', { params: { months: 12 } }),
        ])
        if (!active) return
        setSummary(summaryResponse.data)
        setRevenue(revenueResponse.data?.trend || [])
        setExpenses(expensesResponse.data?.trend || [])
      } catch (err) {
        if (!active) return
        setError(err.response?.data?.detail || t('dashboard.loadError', 'تعذر تحميل بيانات لوحة التحكم'))
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [t])

  const revenueChart = useMemo(() => revenue.map((item) => ({
    date: item.month,
    value: item.revenue,
  })), [revenue])

  const expenseChart = useMemo(() => expenses.map((item) => ({
    month: item.month,
    value: item.expenses,
  })), [expenses])

  const summaryData = summary?.data || summary || {}

  return (
    <div className="fade-in">
      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}

      {loading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="إجمالي الإيرادات" value={summaryData.revenue || 0} precision={2} prefix={<DollarOutlined />} /></Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="المصروفات" value={summaryData.expenses || 0} precision={2} prefix={<FallOutlined />} /></Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="صافي الربح" value={summaryData.profit || 0} precision={2} prefix={<RiseOutlined />} /></Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="المشروعات النشطة" value={summaryData.active_projects || 0} prefix={<ProjectOutlined />} /></Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
            <Col xs={24} lg={12}>
              <Card title="الإيرادات الشهرية">
                {revenueChart.length ? (
                  <Line data={revenueChart} xField="date" yField="value" smooth height={300} />
                ) : <Empty description="لا توجد بيانات إيرادات للفترة الحالية" />}
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="المصروفات الشهرية">
                {expenseChart.length ? (
                  <Bar data={expenseChart} xField="month" yField="value" height={300} />
                ) : <Empty description="لا توجد بيانات مصروفات للفترة الحالية" />}
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="الذمم المدينة" value={summaryData.receivables || 0} precision={2} /></Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="الذمم الدائنة" value={summaryData.payables || 0} precision={2} /></Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="العملاء النشطون" value={summaryData.active_customers || 0} prefix={<TeamOutlined />} /></Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card><Statistic title="هامش الربح" value={summaryData.profit_margin || 0} precision={1} suffix="%" /></Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  )
}

export default DashboardPage
