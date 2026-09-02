import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Form, Input, Button, Card, message, Checkbox } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { authAPI } from '../services/api'

function LoginPage() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useTranslation()

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const response = await authAPI.login(values)
      localStorage.setItem('eos_token', response.data.access_token)
      if (response.data.tenant_id) {
        localStorage.setItem('eos_tenant_id', response.data.tenant_id)
      }
      message.success(t('welcome'))
      navigate((location.state?.from?.pathname) || '/dashboard')
    } catch (error) {
      message.error(error.response?.data?.detail || t('invalid_credentials'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Card
          className="slide-in-right"
          style={{
            width: 400,
            borderRadius: 12,
            boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 30 }}>
            <h1 style={{ 
              fontSize: 32, 
              margin: 0,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>EOS ERP</h1>
            <p style={{ color: '#666', marginTop: 8 }}>{t('welcome')}</p>
          </div>

          <Form
            name="login"
            initialValues={{ remember: true }}
            onFinish={onFinish}
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="email"
              rules={[
                { required: true, message: t('email') + ' ' + t('required') },
                { type: 'email', message: t('email') + ' ' + t('invalid') },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder={t('email')}
                disabled={loading}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: t('password') + ' ' + t('required') }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder={t('password')}
                disabled={loading}
              />
            </Form.Item>

            <Form.Item>
              <Checkbox>{t('remember_me')}</Checkbox>
              <a href="/forgot-password" style={{ float: 'right' }}>
                {t('forgot_password')}
              </a>
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                style={{
                  height: 48,
                  fontSize: 16,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                }}
              >
                {t('sign_in')}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </motion.div>
    </div>
  )
}

export default LoginPage
