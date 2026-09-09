import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Space, message, Grid } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useBrandingStore } from '../stores/brandingStore';

const { Title, Text } = Typography;
const { useBreakpoint } = Grid;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const branding = useBrandingStore((s) => s.branding);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.email, values.password);
      message.success('تم تسجيل الدخول بنجاح');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error?.message || 'خطأ في تسجيل الدخول');
    } finally {
      setLoading(false);
    }
  };

  const isRTL = branding?.direction !== 'ltr';
  const loginTitle = isRTL
    ? branding?.login_title_ar || 'تسجيل الدخول إلى EOS'
    : branding?.login_title_en || 'Login to EOS';
  const loginSubtitle = isRTL
    ? branding?.login_subtitle_ar || 'نظام إدارة المؤسسات'
    : branding?.login_subtitle_en || 'Enterprise Resource Planning';

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: `linear-gradient(135deg, ${branding?.primary_color || '#667eea'} 0%, ${branding?.secondary_color || '#764ba2'} 100%)`,
        padding: isMobile ? 16 : 24,
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 400,
          borderRadius: 12,
          boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            {branding?.logo_url && (
              <img
                src={branding.logo_url}
                alt="logo"
                style={{ height: 48, maxHeight: 60, objectFit: 'contain', marginBottom: 12 }}
              />
            )}
            <Title level={2} style={{ margin: 0, color: branding?.primary_color || undefined }}>
              {loginTitle}
            </Title>
            <Text type="secondary">
              {loginSubtitle}
            </Text>
          </div>

          <Form
            name="login"
            onFinish={onFinish}
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="email"
              rules={[
                { required: true, message: 'أدخل البريد الإلكتروني' },
                { type: 'email', message: 'البريد الإلكتروني غير صحيح' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="البريد الإلكتروني"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: 'أدخل كلمة المرور' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="كلمة المرور"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{ height: 48 }}
              >
                تسجيل الدخول
              </Button>
            </Form.Item>
          </Form>

          <div style={{ textAlign: 'center' }}>
            <Text type="secondary">
              {branding?.show_powered_by !== false ? (
                <>Powered by EOS</>
              ) : (
                <>EOS Platform</>
              )}
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default LoginPage;
