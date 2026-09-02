import React from 'react'
import { Card, Row, Col, List } from 'antd'
import { FileTextOutlined, DollarOutlined, PieChartOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

function ReportsPage() {
  const { t } = useTranslation()

  const financialReports = [
    { title: t('trial_balance'), icon: <FileTextOutlined /> },
    { title: t('profit_loss'), icon: <DollarOutlined /> },
    { title: t('balance_sheet'), icon: <PieChartOutlined /> },
    { title: t('cash_flow'), icon: <DollarOutlined /> },
  ]

  return (
    <div className="fade-in">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title={t('financial_reports')}>
            <List
              itemLayout="horizontal"
              dataSource={financialReports}
              renderItem={(item) => (
                <List.Item hoverable style={{ cursor: 'pointer', padding: '12px 0' }}>
                  <List.Item.Meta
                    avatar={<div style={{ fontSize: 24 }}>{item.icon}</div>}
                    title={item.title}
                    description="تقرير مالي شامل"
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t('operational_reports')}>
            <List
              itemLayout="horizontal"
              dataSource={[
                { title: 'تقرير المبيعات', desc: 'تحليل المبيعات الشهرية' },
                { title: 'تقرير المخزون', desc: 'حركة المخزون الحالية' },
                { title: 'تقرير المشتريات', desc: 'طلبات الشراء المفتوحة' },
              ]}
              renderItem={(item) => (
                <List.Item hoverable style={{ cursor: 'pointer', padding: '12px 0' }}>
                  <List.Item.Meta
                    title={item.title}
                    description={item.desc}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ReportsPage
