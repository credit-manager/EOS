/**
 * EOS System — White-Label Branding Admin Page (P67)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Form,
  Input,
  Button,
  Switch,
  Select,
  ColorPicker,
  message,
  Spin,
  Tabs,
  Tag,
  Modal,
  Alert,
  Divider,
} from 'antd';
import {
  SaveOutlined,
  GlobalOutlined,
  BgColorsOutlined,
  FileTextOutlined,
  FlagOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  DeleteOutlined,
  LockOutlined,
  UnlockOutlined,
} from '@ant-design/icons';
import { whitelabelApi } from '../services';
import { useAuthStore } from '../stores/authStore';
import { useBrandingStore } from '../stores/brandingStore';
import type { TenantBranding, FeatureFlags } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const BrandingPage: React.FC = () => {
  const { user } = useAuthStore();
  const applyLocalOverride = useBrandingStore((s) => s.applyLocalOverride);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [branding, setBranding] = useState<TenantBranding | null>(null);
  const [flags, setFlags] = useState<FeatureFlags | null>(null);
  const [dnsRecord, setDnsRecord] = useState<string | null>(null);
  const [domainInput, setDomainInput] = useState('');
  const [claimModalOpen, setClaimModalOpen] = useState(false);

  const [form] = Form.useForm();

  const tenantId = user?.tenantId || '';
  const isAdmin = user?.roles?.includes('admin');

  const fetchData = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const [brandRes, flagRes] = await Promise.allSettled([
        whitelabelApi.getBranding(tenantId),
        whitelabelApi.getFlags(tenantId),
      ]);
      if (brandRes.status === 'fulfilled') {
        const data = brandRes.value.data;
        setBranding(data);
        form.setFieldsValue(data);
        setDomainInput(data.custom_domain || '');
      }
      if (flagRes.status === 'fulfilled') {
        setFlags(flagRes.value.data);
      }
    } catch {
      message.error('خطأ في تحميل الإعدادات');
    } finally {
      setLoading(false);
    }
  }, [tenantId, form]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSave = async () => {
    if (!tenantId) return;
    setSaving(true);
    try {
      const values = form.getFieldsValue();
      // Convert antd ColorPicker values to hex strings
      const payload: Record<string, any> = { ...values };
      if (payload.primary_color && typeof payload.primary_color === 'object') {
        payload.primary_color = payload.primary_color.toHex?.() || payload.primary_color;
      }
      if (payload.secondary_color && typeof payload.secondary_color === 'object') {
        payload.secondary_color = payload.secondary_color.toHex?.() || payload.secondary_color;
      }

      const res = await whitelabelApi.updateBranding(tenantId, payload);
      setBranding(res.data);
      // Live-apply public-safe fields to current session
      applyLocalOverride({
        system_name_en: res.data.system_name_en,
        system_name_ar: res.data.system_name_ar,
        logo_url: res.data.logo_url,
        favicon_url: res.data.favicon_url,
        primary_color: res.data.primary_color,
        secondary_color: res.data.secondary_color,
        theme_mode: res.data.theme_mode,
        direction: res.data.direction,
        login_title_en: res.data.login_title_en,
        login_title_ar: res.data.login_title_ar,
        login_subtitle_en: res.data.login_subtitle_en,
        login_subtitle_ar: res.data.login_subtitle_ar,
      });
      message.success('تم حفظ الإعدادات بنجاح');
    } catch {
      message.error('خطأ في حفظ الإعدادات');
    } finally {
      setSaving(false);
    }
  };

  const handleFlagToggle = async (flag: keyof FeatureFlags) => {
    if (!tenantId || !flags) return;
    const newVal = !flags[flag];
    try {
      const res = await whitelabelApi.setFlag(tenantId, flag, newVal);
      setFlags(res.data);
      message.success('تم تحديث الإعداد');
    } catch {
      message.error('خطأ في تحديث الإعداد');
    }
  };

  const handleClaimDomain = async () => {
    if (!tenantId || !domainInput.trim()) return;
    try {
      const res = await whitelabelApi.claimDomain(tenantId, domainInput.trim());
      setBranding(res.data);
      setDnsRecord(res.data.dns_txt_record || null);
      setClaimModalOpen(true);
      setFlags((prev) => prev ? { ...prev, enable_custom_domain: true } : prev);
    } catch {
      message.error('خطأ في تسجيل النطاق');
    }
  };

  const handleVerifyDomain = async () => {
    if (!tenantId) return;
    try {
      await whitelabelApi.verifyDomain(tenantId);
      fetchData();
      message.success('تم التحقق من النطاق بنجاح');
    } catch {
      message.error('خطأ في التحقق — تأكد من إضافة سجل TXT');
    }
  };

  const handleRemoveDomain = async () => {
    if (!tenantId) return;
    Modal.confirm({
      title: 'إزالة النطاق المخصص',
      content: 'هل أنت متأكد من إزالة النطاق المخصص؟',
      okText: 'إزالة',
      okButtonProps: { danger: true },
      cancelText: 'إلغاء',
      onOk: async () => {
        try {
          await whitelabelApi.removeDomain(tenantId);
          fetchData();
          setDomainInput('');
          setDnsRecord(null);
          message.success('تمت إزالة النطاق');
        } catch {
          message.error('خطأ في إزالة النطاق');
        }
      },
    });
  };

  if (!isAdmin) {
    return (
      <Alert
        type="warning"
        showIcon
        icon={<LockOutlined />}
        message="غير مصرح"
        description="هذه الصفحة متاحة فقط لمسؤولي النظام (Admin)."
      />
    );
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>الهوية والتنسيق (White-Label)</Title>
          <Tag color="blue">P67</Tag>
        </Space>
      </div>

      <Tabs defaultActiveKey="identity" type="card">
        {/* ── Tab 1: Identity & Colors ── */}
        <TabPane tab={<Space><BgColorsOutlined /> الهوية والتصميم</Space>} key="identity">
          <Card>
            <Form form={form} layout="vertical" onFinish={handleSave}>
              <Row gutter={[24, 16]}>
                <Col xs={24} lg={12}>
                  <Title level={5}>اسم النظام</Title>
                  <Form.Item label="الاسم بالإنجليزية" name="system_name_en">
                    <Input placeholder="EOS Dynamic Business Platform" />
                  </Form.Item>
                  <Form.Item label="الاسم بالعربية" name="system_name_ar">
                    <Input placeholder="EOS — منصة الأعمال المتكاملة" />
                  </Form.Item>
                  <Form.Item label="رابط الشعار (URL)" name="logo_url">
                    <Input placeholder="https://example.com/logo.png" />
                  </Form.Item>
                  <Form.Item label="رابط Favicon" name="favicon_url">
                    <Input placeholder="https://example.com/favicon.ico" />
                  </Form.Item>
                </Col>
                <Col xs={24} lg={12}>
                  <Title level={5}>الألوان والثيم</Title>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item label="اللون الأساسي" name="primary_color">
                        <ColorPicker format="hex" showText />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="اللون الثانوي" name="secondary_color">
                        <ColorPicker format="hex" showText />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item label="الوضع اللوني" name="theme_mode">
                        <Select options={[
                          { value: 'light', label: 'فاتح' },
                          { value: 'dark', label: 'داكن' },
                        ]} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="الاتجاه" name="direction">
                        <Select options={[
                          { value: 'rtl', label: 'من اليمين لليسار (RTL)' },
                          { value: 'ltr', label: 'من اليسار لليمين (LTR)' },
                        ]} />
                      </Form.Item>
                    </Col>
                  </Row>

                  {/* Live preview */}
                  <Card size="small" style={{ background: '#fafafa', marginTop: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>معاينة حية:</Text>
                    <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
                      {branding?.logo_url && (
                        <img src={branding.logo_url} alt="logo" style={{ height: 32, maxWidth: 80, objectFit: 'contain' }} />
                      )}
                      <div>
                        <Text strong style={{ color: branding?.primary_color || '#1890ff', fontSize: 16 }}>
                          {branding?.system_name_ar || 'اسم النظام'}
                        </Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {branding?.system_name_en || 'System Name'}
                        </Text>
                      </div>
                    </div>
                  </Card>
                </Col>
              </Row>

              <Divider />

              <div style={{ textAlign: 'left' }}>
                <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving} size="large">
                  حفظ الإعدادات
                </Button>
              </div>
            </Form>
          </Card>
        </TabPane>

        {/* ── Tab 2: Login Branding ── */}
        <TabPane tab={<Space><FileTextOutlined /> صفحة تسجيل الدخول</Space>} key="login">
          <Card>
            <Form form={form} layout="vertical" onFinish={handleSave}>
              <Row gutter={[24, 16]}>
                <Col xs={24} lg={12}>
                  <Form.Item label="عنوان تسجيل الدخول (إنجليزي)" name="login_title_en">
                    <Input placeholder="Login to EOS" />
                  </Form.Item>
                </Col>
                <Col xs={24} lg={12}>
                  <Form.Item label="عنوان تسجيل الدخول (عربي)" name="login_title_ar">
                    <Input placeholder="تسجيل الدخول إلى EOS" />
                  </Form.Item>
                </Col>
                <Col xs={24} lg={12}>
                  <Form.Item label="العنوان الفرعي (إنجليزي)" name="login_subtitle_en">
                    <Input placeholder="Enterprise Resource Planning" />
                  </Form.Item>
                </Col>
                <Col xs={24} lg={12}>
                  <Form.Item label="العنوان الفرعي (عربي)" name="login_subtitle_ar">
                    <Input placeholder="إدارة موارد مؤسستك في مكان واحد" />
                  </Form.Item>
                </Col>
              </Row>

              {/* Login page preview */}
              <Card size="small" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', marginTop: 16 }}>
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  {branding?.logo_url && (
                    <img src={branding.logo_url} alt="logo" style={{ height: 48, marginBottom: 12 }} />
                  )}
                  <Title level={3} style={{ color: '#fff', margin: 0 }}>
                    {branding?.login_title_ar || 'تسجيل الدخول إلى EOS'}
                  </Title>
                  <Paragraph style={{ color: 'rgba(255,255,255,0.85)', margin: '4px 0 0' }}>
                    {branding?.login_subtitle_ar || 'إدارة موارد مؤسستك في مكان واحد'}
                  </Paragraph>
                </div>
              </Card>

              <div style={{ textAlign: 'left', marginTop: 16 }}>
                <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                  حفظ النصوص
                </Button>
              </div>
            </Form>
          </Card>
        </TabPane>

        {/* ── Tab 3: Emails & Reports ── */}
        <TabPane tab={<Space><FileTextOutlined /> البريد والتقارير</Space>} key="reports">
          <Card>
            <Form form={form} layout="vertical" onFinish={handleSave}>
              <Form.Item label="نص تذييل البريد الإلكتروني" name="email_footer_text">
                <TextArea rows={3} placeholder="This email was sent by your company ERP system." />
              </Form.Item>
              <Form.Item label="نص رأس التقارير" name="report_header_text">
                <TextArea rows={3} placeholder="Company confidential — For internal use only" />
              </Form.Item>
              <Form.Item label="نص تذييل التقارير" name="report_footer_text">
                <TextArea rows={3} placeholder="Generated by your ERP system" />
              </Form.Item>
              <div style={{ textAlign: 'left' }}>
                <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                  حفظ النصوص
                </Button>
              </div>
            </Form>
          </Card>
        </TabPane>

        {/* ── Tab 4: Custom Domain ── */}
        <TabPane tab={<Space><GlobalOutlined /> النطاق المخصص</Space>} key="domain">
          <Card>
            <Alert
              type="info"
              showIcon
              message="النطاق المخصص"
              description="قم بتسجيل نطاق مخصص (مثل erp.company.com) لاستخدامه كعنوان رئيسي لنظامك."
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Input
                  size="large"
                  placeholder="erp.company.com"
                  value={domainInput}
                  onChange={(e) => setDomainInput(e.target.value)}
                  addonBefore={<GlobalOutlined />}
                  disabled={branding?.domain_verified}
                />
              </Col>
              <Col>
                {branding?.domain_verified ? (
                  <Tag icon={<CheckCircleOutlined />} color="success" style={{ fontSize: 14, padding: '4px 12px' }}>
                    نطاق موثّق ✓
                  </Tag>
                ) : (
                  <Space>
                    <Button type="primary" onClick={handleClaimDomain} disabled={!domainInput.trim()}>
                      تسجيل النطاق
                    </Button>
                    {branding?.custom_domain && (
                      <Button onClick={handleVerifyDomain} icon={<CheckCircleOutlined />}>
                        تحقق
                      </Button>
                    )}
                  </Space>
                )}
              </Col>
            </Row>

            {branding?.custom_domain && !branding?.domain_verified && (
              <Alert
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                message="بانتظار التحقق"
                description={
                  <span>
                    أضف سجل TXT في إعدادات DNS للنطاق: <code>{domainInput}</code><br />
                    السجل المطلوب: <code>dns-verification-token</code>
                  </span>
                }
                style={{ marginTop: 16 }}
                action={
                  <Button size="small" onClick={handleRemoveDomain} icon={<DeleteOutlined />} danger>
                    إزالة
                  </Button>
                }
              />
            )}
          </Card>
        </TabPane>

        {/* ── Tab 5: Feature Flags ── */}
        <TabPane tab={<Space><FlagOutlined /> علامات الميزة</Space>} key="flags">
          <Card>
            <Paragraph type="secondary">
              التحكم في العناصر الظاهرة في واجهة النظام. يمكنك إخفاء علامة "مدعوم من EOS" أو تفعيل النطاق المخصص والهوية البصرية.
            </Paragraph>
            {flags && (
              <Row gutter={[16, 16]}>
                {([
                  { key: 'show_powered_by', label: 'إظهار "مدعوم من EOS"', desc: 'إظهار/إخفاء النص في أسفل الشريط الجانبي' },
                  { key: 'enable_custom_domain', label: 'تفعيل النطاق المخصص', desc: 'السماح باستخدام نطاق مخصص للنظام' },
                  { key: 'enable_custom_branding', label: 'تفعيل الهوية البصرية', desc: 'السماح بتغيير الشعار والألوان' },
                  { key: 'enable_custom_login', label: 'تفعيل صفحة الدخول المخصصة', desc: 'السماح بتخصيص عنوان ونص صفحة تسجيل الدخول' },
                ] as { key: keyof FeatureFlags; label: string; desc: string }[]).map(({ key, label, desc }) => (
                  <Col xs={24} sm={12} key={key}>
                    <Card size="small" style={{ border: '1px solid #f0f0f0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <Text strong>{label}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>{desc}</Text>
                        </div>
                        <Switch
                          checked={flags[key]}
                          onChange={() => handleFlagToggle(key)}
                          checkedChildren={<UnlockOutlined />}
                          unCheckedChildren={<LockOutlined />}
                        />
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>
        </TabPane>
      </Tabs>

      {/* DNS claim modal */}
      <Modal
        title="تم تسجيل النطاق"
        open={claimModalOpen}
        onCancel={() => setClaimModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setClaimModalOpen(false)}>إغلاق</Button>,
        ]}
      >
        <Alert
          type="success"
          message="تم تسجيل النطاق بنجاح"
          description="أضف سجل TXT التالي في إعدادات DNS للنطاق ثم اضغط 'تحقق'."
          style={{ marginBottom: 16 }}
        />
        {dnsRecord && (
          <Card size="small" style={{ background: '#f6f8fa' }}>
            <Text strong>نطاق:</Text> <Text code>{domainInput}</Text><br />
            <Text strong>سجل TXT:</Text> <Text code copyable>{dnsRecord}</Text>
          </Card>
        )}
      </Modal>
    </div>
  );
};

export default BrandingPage;
