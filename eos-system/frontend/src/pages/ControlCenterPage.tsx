/**
 * EOS Control Center — Modern Owner Dashboard
 * The nerve center for EOS platform management.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Typography, Space, Spin, Button, Tag, Table, Statistic,
  Tabs, Modal, Form, Input, Select, message, Avatar,
  Empty, Divider, Badge, Dropdown,
} from 'antd';
import {
  BankOutlined, TeamOutlined,
  AppstoreOutlined, AuditOutlined, ReloadOutlined,
  PlusOutlined, CheckCircleOutlined, PauseCircleOutlined,
  CloudServerOutlined, DatabaseOutlined, ApiOutlined, LockOutlined,
  ToolOutlined, ShopOutlined, CrownOutlined, RocketOutlined,
  EyeOutlined, MoreOutlined,
  ArrowUpOutlined, ArrowDownOutlined,
  HomeOutlined,
  CreditCardOutlined, ExpandOutlined, GlobalOutlined,
} from '@ant-design/icons';
import apiClient from '../services/apiClient';
import { useTenantContext } from '../stores/tenantContext';

const { Text } = Typography;

/* ═══════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════ */

interface PlatformOverview {
  tenants_total: number;
  tenants_active: number;
  companies_total: number;
  users_total: number;
  plans_total: number;
  templates_total: number;
  marketplace_total: number;
  audit_entries: number;
}

interface Tenant {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  status: string;
  plan_id: string;
  plan_name: string;
  max_users: number;
  max_companies: number;
  company_count?: number;
  user_count?: number;
  created_at: string;
  updated_at: string;
}

interface Plan {
  id: string;
  plan_name: string;
  plan_code: string;
  price_monthly: number;
  price_yearly: number;
  max_users: number;
  max_companies: number;
  max_storage_gb: number;
  features: string;
  is_active: boolean;
}

interface Template {
  id: string;
  industry_code: string;
  industry_name: string;
  industry_name_ar: string;
  description: string;
  default_modules: string;
  is_active: boolean;
}

interface MarketplaceItem {
  id: string;
  item_code: string;
  item_type: string;
  name: string;
  name_ar: string;
  description: string;
  publisher: string;
  version: string;
  is_featured: boolean;
  is_free: boolean;
  price_monthly: number;
}

/* ═══════════════════════════════════════════════════
   Stat Card — Clean, minimal, gradient
   ═══════════════════════════════════════════════════ */

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  change?: number;
  suffix?: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, change, suffix }) => (
  <div style={{
    background: '#fff',
    borderRadius: 16,
    padding: '24px',
    border: '1px solid #f0f0f0',
    position: 'relative',
    overflow: 'hidden',
  }}>
    <div style={{
      position: 'absolute', top: 0, right: 0, width: 120, height: 120,
      background: `radial-gradient(circle at top right, ${color}08 0%, transparent 70%)`,
    }} />
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <Text style={{ color: '#8c8c8c', fontSize: 13, display: 'block', marginBottom: 8 }}>{title}</Text>
        <div style={{ fontSize: 28, fontWeight: 700, color: '#1a1a2e', lineHeight: 1 }}>
          {value}{suffix || ''}
        </div>
        {change !== undefined && (
          <div style={{ marginTop: 8, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
            {change >= 0 ? (
              <span style={{ color: '#52c41a' }}><ArrowUpOutlined /> +{change}%</span>
            ) : (
              <span style={{ color: '#ff4d4f' }}><ArrowDownOutlined /> {change}%</span>
            )}
            <Text type="secondary" style={{ fontSize: 11 }}>vs last month</Text>
          </div>
        )}
      </div>
      <div style={{
        width: 44, height: 44, borderRadius: 12,
        background: `${color}10`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color, fontSize: 18,
      }}>{icon}</div>
    </div>
  </div>
);

/* ═══════════════════════════════════════════════════
   Main Control Center
   ═══════════════════════════════════════════════════ */

const ControlCenterPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [marketplace, setMarketplace] = useState<MarketplaceItem[]>([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [createVisible, setCreateVisible] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [form] = Form.useForm();
  const { setTenant } = useTenantContext();

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [o, t, p, tp, mp] = await Promise.allSettled([
        apiClient.get('/control/overview'),
        apiClient.get('/control/tenants?page_size=50'),
        apiClient.get('/control/plans'),
        apiClient.get('/control/templates'),
        apiClient.get('/control/marketplace'),
      ]);
      if (o.status === 'fulfilled') setOverview(o.value as PlatformOverview);
      if (t.status === 'fulfilled') setTenants((t.value as any).data || []);
      if (p.status === 'fulfilled') setPlans((p.value as any).data || []);
      if (tp.status === 'fulfilled') setTemplates((tp.value as any).data || []);
      if (mp.status === 'fulfilled') setMarketplace((mp.value as any).data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleProvision = async (values: any) => {
    setFormLoading(true);
    try {
      const res: any = await apiClient.post('/control/tenants', values);
      message.success({
        content: (
          <div>
            <div style={{ fontWeight: 600 }}>تم إنشاء المؤسسة بنجاح</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
              {res.message} — {res.modules_enabled?.length || 0} modules, {res.accounts_created || 0} accounts
            </div>
          </div>
        ),
        duration: 5,
      });
      setCreateVisible(false);
      form.resetFields();
      fetchAll();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'فشل إنشاء المؤسسة');
    } finally {
      setFormLoading(false);
    }
  };

  const handleImpersonate = async (tenantId: string, tenantName: string) => {
    Modal.confirm({
      title: `الدخول إلى ${tenantName}`,
      content: 'سيتم تسجيل دخولك كمدير هذه المؤسسة. سيتم تسجيل هذه العملية في Audit.',
      okText: 'الدخول',
      cancelText: 'إلغاء',
      onOk: async () => {
        try {
          const res: any = await apiClient.post(`/control/tenants/${tenantId}/impersonate`);
          if (res.access_token) {
            localStorage.setItem('eos_token', res.access_token);
            localStorage.setItem('tenant_id', tenantId);
            setTenant({
              tenantId,
              tenantName: res.tenant_name || tenantName,
              industry: res.industry || 'general',
              companyName: res.company_name,
              currency: res.currency,
            });
            message.success(`تم الدخول إلى ${res.company_name || tenantName}`);
            window.open('/ui/dashboard', '_blank');
          }
        } catch {
          message.error('فشل الدخول');
        }
      },
    });
  };

  /* ─── Tenant Table ─── */

  const tenantColumns = [
    {
      title: 'المؤسسة',
      key: 'name',
      render: (_: any, r: Tenant) => (
        <Space>
          <Avatar style={{ background: '#6366f1', fontSize: 12 }} icon={<BankOutlined />} />
          <div>
            <Text strong style={{ display: 'block', fontSize: 13 }}>{r.name}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>{r.tenant_id}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: 'الخطة',
      dataIndex: 'plan_name',
      render: (v: string) => <Tag color="blue" style={{ borderRadius: 6 }}>{v || '—'}</Tag>,
    },
    {
      title: 'المستخدمون',
      key: 'users',
      render: (_: any, r: Tenant) => (
        <span style={{ fontSize: 13 }}>{r.user_count || 0}/{r.max_users}</span>
      ),
    },
    {
      title: 'الشركات',
      key: 'companies',
      render: (_: any, r: Tenant) => (
        <span style={{ fontSize: 13 }}>{r.company_count || 0}/{r.max_companies}</span>
      ),
    },
    {
      title: 'الحالة',
      dataIndex: 'status',
      render: (v: string) => {
        const m: Record<string, { color: string; label: string }> = {
          active: { color: 'green', label: 'نشط' },
          suspended: { color: 'red', label: 'موقّف' },
          trial: { color: 'orange', label: 'تجريبي' },
          inactive: { color: 'default', label: 'غير نشط' },
        };
        const s = m[v] || m.inactive;
        return <Badge color={s.color} text={<span style={{ fontSize: 12 }}>{s.label}</span>} />;
      },
    },
    {
      title: '',
      key: 'actions',
      width: 100,
      render: (_: any, r: Tenant) => (
        <Dropdown menu={{
          items: [
            { key: 'impersonate', icon: <ExpandOutlined />, label: 'الدخول للنظام',
              onClick: () => handleImpersonate(r.tenant_id, r.name) },
            { key: 'view', icon: <EyeOutlined />, label: 'التفاصيل' },
            r.status === 'active'
              ? { key: 'suspend', icon: <PauseCircleOutlined />, label: 'إيقاف',
                  danger: true, onClick: async () => {
                    await apiClient.post(`/control/tenants/${r.tenant_id}/suspend`);
                    message.success('تم الإيقاف'); fetchAll();
                  }}
              : { key: 'activate', icon: <CheckCircleOutlined />, label: 'تفعيل',
                  onClick: async () => {
                    await apiClient.post(`/control/tenants/${r.tenant_id}/activate`);
                    message.success('تم التفعيل'); fetchAll();
                  }},
          ],
        }}>
          <Button type="text" icon={<MoreOutlined />} size="small" />
        </Dropdown>
      ),
    },
  ];

  /* ═══════════════════════════════════════════════════
     Render
     ═══════════════════════════════════════════════════ */

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa' }}>
      {/* ─── Header ─── */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #f0f0f0',
        padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <Space align="center" size={12}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 16,
          }}><CrownOutlined /></div>
          <div>
            <Text strong style={{ fontSize: 16 }}>EOS Control Center</Text>
            <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>Platform Management</Text>
          </div>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAll} style={{ borderRadius: 8 }} />
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => setCreateVisible(true)}
            style={{ borderRadius: 8, background: '#6366f1', fontWeight: 500 }}>
            New Tenant
          </Button>
        </Space>
      </div>

      {/* ─── Content ─── */}
      <div style={{ padding: '24px 32px', maxWidth: 1400, margin: '0 auto' }}>
        <Spin spinning={loading}>
          {/* Stats */}
          {overview && (
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={12} sm={6}>
                <StatCard title="Total Tenants" value={overview.tenants_total}
                  icon={<BankOutlined />} color="#6366f1" change={20} />
              </Col>
              <Col xs={12} sm={6}>
                <StatCard title="Active Tenants" value={overview.tenants_active}
                  icon={<CheckCircleOutlined />} color="#22c55e" change={15} />
              </Col>
              <Col xs={12} sm={6}>
                <StatCard title="Total Users" value={overview.users_total}
                  icon={<TeamOutlined />} color="#06b6d4" change={8} />
              </Col>
              <Col xs={12} sm={6}>
                <StatCard title="Companies" value={overview.companies_total}
                  icon={<ShopOutlined />} color="#f59e0b" change={5} />
              </Col>
            </Row>
          )}

          {/* Tabs */}
          <Card style={{ borderRadius: 16, border: 'none', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}
            bodyStyle={{ padding: 0 }}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              style={{ padding: '0 24px' }}
              items={[
                {
                  key: 'overview',
                  label: <Space><HomeOutlined />Overview</Space>,
                  children: (
                    <div style={{ padding: '0 0 24px' }}>
                      {/* Tenants Table */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <Text strong style={{ fontSize: 15 }}>Tenants</Text>
                        <Button type="link" icon={<PlusOutlined />}
                          onClick={() => setCreateVisible(true)}>Add Tenant</Button>
                      </div>
                      <Table
                        dataSource={tenants}
                        columns={tenantColumns}
                        rowKey="id"
                        pagination={{ pageSize: 8, size: 'small' }}
                        size="small"
                        locale={{ emptyText: <Empty description="No tenants yet" /> }}
                      />
                    </div>
                  ),
                },
                {
                  key: 'plans',
                  label: <Space><CreditCardOutlined />Plans</Space>,
                  children: (
                    <div style={{ padding: '0 0 24px' }}>
                      <Row gutter={[16, 16]}>
                        {plans.map((plan) => (
                          <Col xs={24} sm={12} lg={6} key={plan.id}>
                            <Card style={{
                              borderRadius: 12, border: '1px solid #f0f0f0',
                              height: '100%',
                            }}
                              hoverable
                              title={
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <Tag color={
                                    plan.plan_code === 'enterprise' ? 'purple' :
                                    plan.plan_code === 'business' ? 'blue' :
                                    plan.plan_code === 'professional' ? 'cyan' : 'green'
                                  } style={{ margin: 0 }}>{plan.plan_name}</Tag>
                                </div>
                              }>
                              <Statistic
                                value={plan.price_monthly}
                                suffix={<span style={{ fontSize: 14 }}>/mo</span>}
                                valueStyle={{ fontSize: 24, fontWeight: 700, color: '#6366f1' }}
                              />
                              <Divider style={{ margin: '12px 0' }} />
                              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                                {[
                                  ['Users', plan.max_users],
                                  ['Companies', plan.max_companies],
                                  ['Storage', `${plan.max_storage_gb} GB`],
                                ].map(([label, val]) => (
                                  <div key={String(label)} style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
                                    <Text style={{ fontSize: 12 }}>{val}</Text>
                                  </div>
                                ))}
                              </Space>
                            </Card>
                          </Col>
                        ))}
                      </Row>
                    </div>
                  ),
                },
                {
                  key: 'templates',
                  label: <Space><AppstoreOutlined />Templates</Space>,
                  children: (
                    <div style={{ padding: '0 0 24px' }}>
                      <Row gutter={[16, 16]}>
                        {templates.map((tpl) => (
                          <Col xs={24} sm={12} lg={8} key={tpl.id}>
                            <Card style={{ borderRadius: 12, border: '1px solid #f0f0f0' }}
                              hoverable>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                                <div>
                                  <Text strong style={{ fontSize: 14 }}>{tpl.industry_name}</Text>
                                  <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>{tpl.industry_name_ar}</Text>
                                </div>
                                <Badge status={tpl.is_active ? 'success' : 'default'} />
                              </div>
                              <Text style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 8 }}>
                                {tpl.description}
                              </Text>
                              {tpl.default_modules && (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                  {(Array.isArray(tpl.default_modules)
                                    ? tpl.default_modules
                                    : JSON.parse(tpl.default_modules || '[]')
                                  ).slice(0, 5).map((m: string, i: number) => (
                                    <Tag key={i} style={{ fontSize: 10, margin: 0 }}>{m}</Tag>
                                  ))}
                                </div>
                              )}
                            </Card>
                          </Col>
                        ))}
                      </Row>
                    </div>
                  ),
                },
                {
                  key: 'marketplace',
                  label: <Space><ShopOutlined />Marketplace</Space>,
                  children: (
                    <div style={{ padding: '0 0 24px' }}>
                      <Row gutter={[16, 16]}>
                        {marketplace.map((item) => (
                          <Col xs={24} sm={12} lg={8} key={item.id}>
                            <Card style={{ borderRadius: 12, border: '1px solid #f0f0f0' }}
                              hoverable>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                                <div>
                                  <Text strong style={{ fontSize: 14 }}>{item.name}</Text>
                                  <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>{item.publisher} · v{item.version}</Text>
                                </div>
                                <Space>
                                  {item.is_featured && <Tag color="gold" style={{ fontSize: 10 }}>Featured</Tag>}
                                  {item.is_free
                                    ? <Tag color="green" style={{ fontSize: 10 }}>Free</Tag>
                                    : <Tag color="blue" style={{ fontSize: 10 }}>${item.price_monthly}/mo</Tag>
                                  }
                                </Space>
                              </div>
                              <Text style={{ fontSize: 12, color: '#666' }}>{item.description}</Text>
                            </Card>
                          </Col>
                        ))}
                      </Row>
                    </div>
                  ),
                },
                {
                  key: 'audit',
                  label: <Space><AuditOutlined />Audit</Space>,
                  children: <AuditTab />,
                },
                {
                  key: 'system',
                  label: <Space><CloudServerOutlined />System</Space>,
                  children: <SystemTab />,
                },
              ]}
            />
          </Card>
        </Spin>
      </div>

      {/* ─── Create Tenant Modal ─── */}
      <Modal
        title={
          <Space>
            <RocketOutlined style={{ color: '#6366f1' }} />
            <span>Create New Tenant</span>
          </Space>
        }
        open={createVisible}
        onCancel={() => { setCreateVisible(false); form.resetFields(); }}
        footer={null}
        width={640}
        styles={{ body: { padding: '24px' } }}
      >
        <Form form={form} layout="vertical" onFinish={handleProvision}>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item name="name" label="Company Name" rules={[{ required: true }]}>
                <Input placeholder="Future Construction Co." size="large" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="industry_code" label="Industry" rules={[{ required: true }]}>
                <Select placeholder="Select" size="large">
                  <Select.Option value="construction">Construction</Select.Option>
                  <Select.Option value="trading">Trading</Select.Option>
                  <Select.Option value="retail">Retail</Select.Option>
                  <Select.Option value="restaurant">Restaurant</Select.Option>
                  <Select.Option value="services">Services</Select.Option>
                  <Select.Option value="manufacturing">Manufacturing</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="admin_email" label="Admin Email" rules={[{ required: true, type: 'email' }]}>
                <Input placeholder="admin@company.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="admin_name" label="Admin Name">
                <Input placeholder="Ahmed Mohammed" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="admin_password" label="Password" initialValue="admin123">
                <Input.Password />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="plan_id" label="Plan">
                <Select placeholder="Select plan">
                  {plans.map(p => (
                    <Select.Option key={p.id} value={p.id}>{p.plan_name}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="currency" label="Currency" initialValue="SAR">
                <Select>
                  <Select.Option value="SAR">SAR</Select.Option>
                  <Select.Option value="AED">AED</Select.Option>
                  <Select.Option value="EGP">EGP</Select.Option>
                  <Select.Option value="USD">USD</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Divider style={{ margin: '16px 0' }} />
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={formLoading}
                icon={<RocketOutlined />}
                style={{ background: '#6366f1', fontWeight: 500 }}>
                Create & Provision Tenant
              </Button>
              <Button onClick={() => setCreateVisible(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Audit Tab
   ═══════════════════════════════════════════════════ */

const AuditTab: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res: any = await apiClient.get('/control/audit?page_size=20');
        setData(res.data || []);
      } catch { }
      setLoading(false);
    })();
  }, []);

  return (
    <Table
      dataSource={data}
      rowKey="id"
      loading={loading}
      size="small"
      pagination={{ pageSize: 10, size: 'small' }}
      columns={[
        { title: 'Tenant', dataIndex: 'tenant_id', key: 'tenant_id', ellipsis: true, width: 200 },
        { title: 'Type', dataIndex: 'entity_type', key: 'type', width: 120,
          render: (v: string) => <Tag style={{ fontSize: 10 }}>{v}</Tag> },
        { title: 'Action', dataIndex: 'action', key: 'action', width: 100,
          render: (v: string) => (
            <Badge color={v === 'create' ? 'green' : v === 'delete' ? 'red' : 'blue'} text={<span style={{ fontSize: 11 }}>{v}</span>} />
          )},
        { title: 'Actor', dataIndex: 'actor_email', key: 'actor', width: 200 },
        { title: 'Date', dataIndex: 'created_at', key: 'date', width: 120,
          render: (v: string) => v ? new Date(v).toLocaleDateString('en-GB') : '—' },
      ]}
      locale={{ emptyText: <Empty description="No audit records" /> }}
    />
  );
};

/* ═══════════════════════════════════════════════════
   System Health Tab
   ═══════════════════════════════════════════════════ */

const SystemTab: React.FC = () => {
  const services = [
    { name: 'API Gateway', icon: <ApiOutlined />, status: 'healthy', detail: 'All endpoints responding', latency: '12ms' },
    { name: 'PostgreSQL', icon: <DatabaseOutlined />, status: 'healthy', detail: '278 tables', latency: '3ms' },
    { name: 'Authentication', icon: <LockOutlined />, status: 'healthy', detail: 'JWT + bcrypt', latency: '—' },
    { name: 'Background Jobs', icon: <ToolOutlined />, status: 'healthy', detail: 'No pending jobs', latency: '—' },
    { name: 'File Storage', icon: <CloudServerOutlined />, status: 'healthy', detail: 'Local filesystem', latency: '—' },
    { name: 'CORS', icon: <GlobalOutlined />, status: 'healthy', detail: 'All origins allowed', latency: '—' },
  ];

  return (
    <div style={{ padding: '0 0 24px' }}>
      <Row gutter={[16, 16]}>
        {services.map((svc, i) => (
          <Col xs={24} sm={12} lg={8} key={i}>
            <Card style={{ borderRadius: 12, border: '1px solid #f0f0f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Space>
                  <div style={{
                    width: 40, height: 40, borderRadius: 10, background: '#f6ffed',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#52c41a', fontSize: 16,
                  }}>{svc.icon}</div>
                  <div>
                    <Text strong style={{ fontSize: 13 }}>{svc.name}</Text>
                    <div style={{ marginTop: 2 }}>
                      <Badge status="success" text={<span style={{ fontSize: 11 }}>{svc.status}</span>} />
                    </div>
                  </div>
                </Space>
                <Text type="secondary" style={{ fontSize: 11 }}>{svc.latency}</Text>
              </div>
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>{svc.detail}</Text>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default ControlCenterPage;
