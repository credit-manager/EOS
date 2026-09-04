import React, { useState } from 'react'
import { Alert, Button, Card, Form, Input, Progress, Steps, Tag } from 'antd'
import { useTranslation } from 'react-i18next'
import { builderAPI } from '../services/api'

const { TextArea } = Input

function BuilderPage() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [buildResult, setBuildResult] = useState(null)
  const [error, setError] = useState(null)
  const { t } = useTranslation()

  const handleCompose = async ({ description }) => {
    setLoading(true)
    setError(null)
    try {
      const response = await builderAPI.compose(description)
      const data = response.data?.data || response.data
      setBuildResult(data)
      setCurrentStep(1)
    } catch (err) {
      setError(err.response?.data?.detail?.error?.message || err.response?.data?.detail || 'فشل في توليد النظام')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    const sessionId = buildResult?.session_id
    if (!sessionId) return
    setLoading(true)
    setError(null)
    try {
      await builderAPI.approve(sessionId)
      await builderAPI.activate(sessionId)
      setCurrentStep(2)
    } catch (err) {
      setError(err.response?.data?.detail?.error?.message || err.response?.data?.detail || 'فشل في اعتماد وتفعيل النظام')
    } finally {
      setLoading(false)
    }
  }

  const config = buildResult?.config || {}
  const validation = buildResult?.validation || {}

  return (
    <div className="fade-in">
      <Steps current={currentStep} style={{ marginBottom: 32 }}>
        <Steps.Step title={t('business_description')} />
        <Steps.Step title={t('modules_selected')} />
        <Steps.Step title={t('published')} />
      </Steps>

      {currentStep === 0 && (
        <Card title={t('build_erp')} size="large">
          <Form form={form} onFinish={handleCompose} layout="vertical" size="large">
            <Form.Item label={t('business_description')} name="description" rules={[{ required: true, message: 'يرجى وصف نشاطك التجاري' }]}>
              <TextArea rows={6} placeholder={t('describe_business')} disabled={loading} style={{ fontSize: 16 }} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} size="large" block>{t('ai_compose')}</Button>
            </Form.Item>
            <Alert message="مثال على الوصف" description="أريد نظام ERP لشركة مقاولات متخصصة في المشاريع السكنية والتجارية، مع إدارة للمشاريع والمخازن والموظفين والحسابات" type="info" showIcon />
          </Form>
        </Card>
      )}

      {currentStep === 1 && buildResult && (
        <div>
          <Card title={t('modules_selected')} size="large" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
              {config.modules?.map((module) => <Tag key={module} color="blue">{module}</Tag>)}
            </div>
            <p>الصناعة المكتشفة: <strong>{config.industry || buildResult.requirements?.industry || 'general'}</strong></p>
            <p>الوحدات: {validation.modules_count || config.modules?.length || 0} — الكيانات: {validation.entities_count || config.entities?.length || 0}</p>
            {validation.warnings?.length > 0 && <Alert type="warning" showIcon message={validation.warnings.join(' | ')} style={{ marginBottom: 16 }} />}
            <h3>{t('entities_created')}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              {config.entities?.map((entity, index) => <Card key={`${entity.name || entity.code}-${index}`} size="small"><strong>{entity.name || entity.code}</strong><div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{entity.fields?.length || 0} حقول</div></Card>)}
            </div>
          </Card>
          <Button type="primary" onClick={handlePublish} loading={loading} disabled={!buildResult.session_id}>{t('publish')}</Button>
        </div>
      )}

      {currentStep === 2 && (
        <Card title={t('published')}>
          <Progress percent={100} status="success" />
          <Alert message={t('success')} type="success" showIcon />
        </Card>
      )}

      {error && <Alert message={error} type="error" showIcon style={{ marginTop: 16 }} />}
    </div>
  )
}

export default BuilderPage
