import React from 'react'
import { Card, Row, Col, Statistic, Progress } from 'antd'
import {
  DollarOutlined,
  TeamOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { Line, Bar, Pie } from '@ant-design/charts'

function DashboardPage() {
  const { t } = useTranslation()

  const lineData = [
    { date: '2024-01', value: 12000 },
    { date: '2024-02', value: 15000 },
    { date: '2024-03', value: 18000 },
    { date: '2024-04', value: 22000 },
    { date: '2024-05', value: 28000 },
    { date: '2024-06', value: 35000 },
  ]

  const barData = [
    { category: 'المبيعات', value: 45000 },
    { category: 'المشتريات', value: 28000 },
    { category: 'المخزون', value: 15000 },
    { category: 'الرواتب', value: 22000 },
  ]

  const pieData = [
    { type: 'نقدي', value: 45 },
    { type: 'آجل', value: 35 },
    { type: 'شيكات', value: 20 },
  ]

  const lineConfig = {
    data: lineData,
    xField: 'date',
    yField: 'value',
    smooth: true,
    color: '#1890ff',
    height: 300,
  }

  const barConfig = {
    data: barData,
    xField: 'category',
    yField: 'value',
    color: '#52c41a',
    height: 300,
  }

  const pieConfig = {
    data: pieData,
    angleField: 'value',
    colorField: 'type',
    radius: 0.8,
    height: 300,
    label: {
      type: 'outer',
      content: '{name} {percentage}',
    },
  }

  return (
    <div className="fade-in">
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="إجمالي الإيرادات"
              value={125430}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="ر.س"
              valueStyle={{ color: '#52c41a' }}
            />
            <Progress percent={78} strokeColor="#52c41a" style={{ marginTop: 16 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="عدد الموظفين"
              value={156}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            <Progress percent={65} strokeColor="#1890ff" style={{ marginTop: 16 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="الفواتير المفتوحة"
              value={48}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
            <Progress percent={45} strokeColor="#faad14" style={{ marginTop: 16 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="المهام المكتملة"
              value={234}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
            <Progress percent={89} strokeColor="#722ed1" style={{ marginTop: 16 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="تحليل الإيرادات الشهرية">
            <Line {...lineConfig} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="توزيع المصروفات">
            <Bar {...barConfig} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="طرق الدفع">
            <Pie {...pieConfig} />
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="آخر الأنشطة">
            <div style={{ padding: '20px 0' }}>
              <p>✓ تم إنشاء فاتورة جديدة #INV-2024-001</p>
              <p>✓ تم اعتماد طلب شراء #PO-2024-045</p>
              <p>✓ تم إضافة موظف جديد - أحمد محمد</p>
              <p>✓ تم إتمام عملية بيع #SO-2024-089</p>
              <p>✓ تم تحديث المخزون - مستودع الرياض</p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage
