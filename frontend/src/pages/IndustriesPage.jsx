import React from 'react'
import { Card, Row, Col, Typography, Tag } from 'antd'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  BuildOutlined,
  CloudOutlined,
  ShopOutlined,
  FactoryOutlined,
  ShoppingOutlined,
  CoffeeOutlined,
  HeartOutlined,
  BookOutlined,
  HomeOutlined,
  CarOutlined,
} from '@ant-design/icons'

const { Title, Paragraph } = Typography

const industries = [
  { 
    key: 'construction', 
    title: 'construction', 
    icon: <BuildOutlined />, 
    color: '#1890ff',
    description: 'إدارة المشاريع والمقاولات الشاملة'
  },
  { 
    key: 'tourism', 
    title: 'tourism', 
    icon: <CloudOutlined />, 
    color: '#52c41a',
    description: 'أنظمة السياحة والسفر والحجوزات'
  },
  { 
    key: 'trading', 
    title: 'trading', 
    icon: <ShopOutlined />, 
    color: '#faad14',
    description: 'التجارة والتوزيع وسلاسل الإمداد'
  },
  { 
    key: 'manufacturing', 
    title: 'manufacturing', 
    icon: <FactoryOutlined />, 
    color: '#722ed1',
    description: 'التصنيع وإدارة خطوط الإنتاج'
  },
  { 
    key: 'retail', 
    title: 'retail', 
    icon: <ShoppingOutlined />, 
    color: '#eb2f96',
    description: 'التجزئة ونقاط البيع المتكاملة'
  },
  { 
    key: 'restaurant', 
    title: 'restaurant', 
    icon: <CoffeeOutlined />, 
    color: '#fa8c16',
    description: 'المطاعم وإدارة المطابخ'
  },
  { 
    key: 'healthcare', 
    title: 'healthcare', 
    icon: <HeartOutlined />, 
    color: '#f5222d',
    description: 'الرعاية الصحية والعيادات'
  },
  { 
    key: 'education', 
    title: 'education', 
    icon: <BookOutlined />, 
    color: '#13c2c2',
    description: 'المؤسسات التعليمية والمدارس'
  },
  { 
    key: 'real_estate', 
    title: 'real_estate', 
    icon: <HomeOutlined />, 
    color: '#2f54eb',
    description: 'العقارات وإدارة الأملاك'
  },
  { 
    key: 'automotive', 
    title: 'automotive', 
    icon: <CarOutlined />, 
    color: '#8c8c8c',
    description: 'السيارات وقطع الغيار'
  },
]

function IndustriesPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const handleSelectIndustry = (key) => {
    navigate(`/builder?industry=${key}`)
  }

  return (
    <div className="fade-in">
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <Title level={2}>{t('select_industry')}</Title>
        <Paragraph style={{ fontSize: 16, color: '#666' }}>
          اختر القطاع المناسب لنشاطك التجاري لبدء بناء نظام ERP المخصص
        </Paragraph>
      </div>

      <Row gutter={[24, 24]}>
        {industries.map((industry, index) => (
          <Col xs={24} sm={12} md={8} lg={6} key={industry.key}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ scale: 1.05 }}
              onClick={() => handleSelectIndustry(industry.key)}
              style={{ cursor: 'pointer' }}
            >
              <Card
                hoverable
                style={{
                  height: '100%',
                  textAlign: 'center',
                  borderRadius: 12,
                  border: `2px solid ${industry.color}`,
                }}
              >
                <div style={{ 
                  fontSize: 48, 
                  color: industry.color, 
                  marginBottom: 16 
                }}>
                  {industry.icon}
                </div>
                <Title level={4} style={{ margin: '12px 0' }}>
                  {t(industry.title)}
                </Title>
                <Paragraph style={{ color: '#666', marginBottom: 16 }}>
                  {industry.description}
                </Paragraph>
                <Tag color={industry.color}>ابدأ الآن</Tag>
              </Card>
            </motion.div>
          </Col>
        ))}
      </Row>
    </div>
  )
}

export default IndustriesPage
