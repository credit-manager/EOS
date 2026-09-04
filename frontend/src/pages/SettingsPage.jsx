import React from 'react'
import { Card, Form, Input, Button, Select, Switch } from 'antd'
import { useTranslation } from 'react-i18next'

function SettingsPage() {
  const { t, i18n } = useTranslation()

  return (
    <div className="fade-in">
      <Card title={t('settings')} style={{ maxWidth: 800 }}>
        <Form layout="vertical" size="large">
          <Form.Item label={t('language')}>
            <Select 
              value={i18n.language} 
              onChange={(lng) => i18n.changeLanguage(lng)}
              options={[
                { value: 'ar', label: '🇸🇦 العربية' },
                { value: 'en', label: '🇬🇧 English' },
                { value: 'fr', label: '🇫🇷 Français' },
                { value: 'de', label: '🇩🇪 Deutsch' },
                { value: 'es', label: '🇪🇸 Español' },
                { value: 'zh', label: '🇨🇳 中文' },
              ]}
            />
          </Form.Item>
          
          <Form.Item label="البريد الإلكتروني">
            <Input value="admin@company.com" disabled />
          </Form.Item>
          
          <Form.Item label="اسم الشركة">
            <Input defaultValue="شركة المثال" />
          </Form.Item>
          
          <Form.Item label="العملة الافتراضية">
            <Select defaultValue="SAR">
              <Select.Option value="SAR">ريال سعودي</Select.Option>
              <Select.Option value="USD">دولار أمريكي</Select.Option>
              <Select.Option value="EUR">يورو</Select.Option>
              <Select.Option value="AED">درهم إماراتي</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item label="الإشعارات">
            <Switch defaultChecked />
          </Form.Item>
          
          <Form.Item>
            <Button type="primary" htmlType="submit">
              {t('save')}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default SettingsPage
