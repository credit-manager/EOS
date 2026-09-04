import React, { useState } from 'react'
import { Card, Form, Input, Button, Steps, Alert, Tag, Progress } from 'antd'
import { useTranslation } from 'react-i18next'
import { builderAPI } from '../services/api'

const { TextArea } = Input
const { Step } = Steps

function BuilderPage() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [buildResult, setBuildResult] = useState(null)
  const [error, setError] = useState(null)
  const { t } = useTranslation()

  const handleCompose = async (values) => { setLoading(true); setError(null); try { const response = await builderAPI.compose(values.description); setBuildResult(response.data); setCurrentStep(1) } catch (err) { setError(err.response?.data?.detail || 'فشل في توليد النظام') } finally { setLoading(false) } }
  const handlePublish = async () => { if (!buildResult?.config_id) return; setLoading(true); try { await builderAPI.publish(buildResult.config_id); setCurrentStep(2) } catch { setError('فشل في نشر النظام') } finally { setLoading(false) } }
  return (<div className="fade-in"><Steps current={currentStep} style={{ marginBottom: 32 }}><Step title={t('business_description')} /><Step title={t('modules_selected')} /><Step title={t('published')} /></Steps>{currentStep === 0 && (<Card title={t('build_erp')} size="large"><Form form={form} onFinish={handleCompose} layout="vertical" size="large"><Form.Item label={t('business_description')} name="description" rules={[{ required: true, message: 'يرجى وصف نشاطك التجاري' }]}><TextArea rows={6} placeholder={t('describe_business')} disabled={loading} style={{ fontSize: 16 }} /></Form.Item><Form.Item><Button type="primary" htmlType="submit" loading={loading} size="large" block>{t('ai_compose')}</Button></Form.Item><Alert message="مثال على الوصف" description="أريد نظام ERP لشركة مقاولات متخصصة في المشاريع السكنية والتجارية، مع إدارة للمشاريع والمخازن والموظفين والحسابات" type="info" showIcon style={{ marginTop: 16 }} /></Form></Card>)}{currentStep === 1 && buildResult && (<div><Card title={t('modules_selected')} size="large" style={{ marginBottom: 16 }}><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>{buildResult.modules?.map((module, idx) => <Tag key={idx} color="blue">{module}</Tag>)}</div><h3>{t('entities_created')}</h3><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>{buildResult.entities?.map((entity, idx) => <Card key={idx} size="small" hoverable><strong>{entity.name}</strong><div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{entity.fields?.length || 0} حقول</div></Card>)}</div>{buildResult.workflows && (<><h3 style={{ marginTop: 24 }}>{t('workflows_configured')}</h3><p>{buildResult.workflows.length} workflows</p></>)}</Card><Button type="primary" onClick={handlePublish} loading={loading}>{t('publish')}</Button></div>)}{currentStep === 2 && (<Card title={t('published')}><Progress percent={100} status="success" /><Alert message={t('success')} type="success" showIcon /></Card>)}{error && <Alert message={error} type="error" showIcon style={{ marginTop: 16 }} />}</div>)
}
export default BuilderPage
