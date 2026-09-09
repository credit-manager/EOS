/**
 * EOS System — Modern Executive Dashboard (P67.5)
 * Enterprise-grade UI inspired by Dynamics 365 / SAP Fiori
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Select,
  Spin,
  Button,
  Tag,
  List,
  Avatar,
  Progress,
  Empty,
  Statistic,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  DollarOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  ProjectOutlined,
  ReloadOutlined,
  AlertOutlined,
  BankOutlined,
  ShopOutlined,
  FileTextOutlined,
  RiseOutlined,
  MinusOutlined,
  PlusOutlined,
  TrophyOutlined,
  ApartmentOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { analyticsApi } from '../services';
import { useAuthStore } from '../stores/authStore';
import type {
  KPI,
  RevenueTrendPoint,
  ProfitTrendPoint,
  TopCustomer,
  BusinessAlert,
  ProjectSummary,
  HRSummary,
  InventorySummary,
} from '../types';

const { Title, Text } = Typography;

const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];
const GRADIENT_COLORS = {
  primary: ['#6366f1', '#818cf8'],
  success: ['#22c55e', '#4ade80'],
  warning: ['#f59e0b', '#fbbf24'],
  danger: ['#ef4444', '#f87171'],
  info: ['#06b6d4', '#22d3ee'],
  purple: ['#8b5cf6', '#a78bfa'],
};

const formatCurrency = (value: number) => {
  if (Math.abs(value) >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toFixed(0);
};

const formatMonth = (month: string) => {
  const d = new Date(month);
  return d.toLocaleDateString('ar-EG', { month: 'short', year: '2-digit' });
};

// ═══════════════════════════════════════════════════
// Modern KPI Card Component
// ═══════════════════════════════════════════════════

interface KPICardProps {
  title: string;
  value: number;
  format?: 'currency' | 'number' | 'percent';
  trend?: 'up' | 'down' | 'neutral';
  change?: number;
  icon: React.ReactNode;
  gradient: string[];
  sparklineData?: number[];
}

const ModernKPICard: React.FC<KPICardProps> = ({
  title,
  value,
  format = 'number',
  trend = 'neutral',
  change = 0,
  icon,
  gradient,
  sparklineData = [],
}) => {
  const isPositive = trend === 'up';
  const isNegative = trend === 'down';

  const formatValue = (v: number) => {
    if (format === 'currency') return `${formatCurrency(v)} ج.م`;
    if (format === 'percent') return `${v.toFixed(1)}%`;
    return v.toLocaleString();
  };

  return (
    <div
      style={{
        background: `linear-gradient(135deg, ${gradient[0]} 0%, ${gradient[1]} 100%)`,
        borderRadius: 16,
        padding: '24px',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        minHeight: 160,
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      {/* Background decoration */}
      <div style={{
        position: 'absolute', top: -20, right: -20,
        width: 100, height: 100, borderRadius: '50%',
        background: 'rgba(255,255,255,0.1)',
      }} />
      <div style={{
        position: 'absolute', bottom: -30, left: -30,
        width: 80, height: 80, borderRadius: '50%',
        background: 'rgba(255,255,255,0.05)',
      }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: 14, fontWeight: 500 }}>
          {title}
        </Text>
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: 'rgba(255,255,255,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18, backdropFilter: 'blur(4px)',
        }}>
          {icon}
        </div>
      </div>

      <div style={{ fontSize: 32, fontWeight: 700, marginBottom: 8, lineHeight: 1 }}>
        {formatValue(value)}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Tag
          color={isPositive ? 'rgba(34,197,94,0.2)' : isNegative ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.2)'}
          style={{
            margin: 0, border: 'none',
            color: isPositive ? '#86efac' : isNegative ? '#fca5a5' : '#d1d5db',
            fontWeight: 600, fontSize: 12,
          }}
        >
          {isPositive ? <ArrowUpOutlined /> : isNegative ? <ArrowDownOutlined /> : <MinusOutlined />}
          {' '}{Math.abs(change)}%
        </Tag>
        <Text style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>
          مقارنة بالفترة السابقة
        </Text>
      </div>

      {/* Mini sparkline */}
      {sparklineData.length > 0 && (
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 40, opacity: 0.3 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparklineData.map((v, i) => ({ v, i }))}>
              <defs>
                <linearGradient id={`spark-${gradient[0].replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#fff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#fff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke="#fff"
                strokeWidth={1.5}
                fill={`url(#spark-${gradient[0].replace('#', '')})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════
// Modern Chart Card Component
// ═══════════════════════════════════════════════════

interface ChartCardProps {
  title: string;
  icon: React.ReactNode;
  extra?: React.ReactNode;
  children: React.ReactNode;
  height?: number;
}

const ChartCard: React.FC<ChartCardProps> = ({ title, icon, extra, children, height = 320 }) => (
  <Card
    style={{
      borderRadius: 16,
      border: 'none',
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
    }}
    bodyStyle={{ padding: '20px 24px' }}
    title={
      <Space size={12}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontSize: 16,
        }}>
          {icon}
        </div>
        <Text strong style={{ fontSize: 15 }}>{title}</Text>
      </Space>
    }
    extra={extra}
  >
    <div style={{ height }}>
      {children}
    </div>
  </Card>
);

// ═══════════════════════════════════════════════════
// Quick Action Button Component
// ═══════════════════════════════════════════════════

interface QuickActionProps {
  icon: React.ReactNode;
  label: string;
  color: string;
  onClick: () => void;
}

const QuickAction: React.FC<QuickActionProps> = ({ icon, label, color, onClick }) => (
  <div
    onClick={onClick}
    style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
      padding: '16px 12px', borderRadius: 12, cursor: 'pointer',
      background: '#fafafa', border: '1px solid #f0f0f0',
      transition: 'all 0.2s',
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.background = `${color}08`;
      e.currentTarget.style.borderColor = `${color}30`;
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.background = '#fafafa';
      e.currentTarget.style.borderColor = '#f0f0f0';
    }}
  >
    <div style={{
      width: 44, height: 44, borderRadius: 12,
      background: `${color}10`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color, fontSize: 20,
    }}>
      {icon}
    </div>
    <Text style={{ fontSize: 12, fontWeight: 500 }}>{label}</Text>
  </div>
);

// ═══════════════════════════════════════════════════
// Main Dashboard Component
// ═══════════════════════════════════════════════════

const DashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('this_month');

  const [kpis, setKpis] = useState<KPI[]>([]);
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendPoint[]>([]);
  const [profitTrend, setProfitTrend] = useState<ProfitTrendPoint[]>([]);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [alerts, setAlerts] = useState<BusinessAlert[]>([]);
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null);
  const [hrSummary, setHrSummary] = useState<HRSummary | null>(null);
  const [inventorySummary, setInventorySummary] = useState<InventorySummary | null>(null);

  const tenantId = user?.tenantId || '';

  const fetchData = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const [, kpisRes, revenueRes, profitRes,,
        customersRes, alertsRes, projectRes, hrRes, invRes,
      ] = await Promise.allSettled([
        analyticsApi.getExecutiveSummary(tenantId, period),
        analyticsApi.getKPIs(tenantId, period),
        analyticsApi.getRevenueTrend(tenantId, 12),
        analyticsApi.getProfitTrend(tenantId, 12),
        Promise.resolve({ status: 'fulfilled' as const, value: {} as any }),
        analyticsApi.getTopCustomers(tenantId, 5),
        analyticsApi.getAlerts(tenantId),
        analyticsApi.getProjectSummary(tenantId),
        analyticsApi.getHRSummary(tenantId),
        analyticsApi.getInventorySummary(tenantId),
      ]);

      if (kpisRes.status === 'fulfilled') setKpis(kpisRes.value.kpis || []);
      if (revenueRes.status === 'fulfilled') setRevenueTrend(revenueRes.value.trend || []);
      if (profitRes.status === 'fulfilled') setProfitTrend(profitRes.value.trend || []);
      if (customersRes.status === 'fulfilled') setTopCustomers(customersRes.value.customers || []);
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value.alerts || []);
      if (projectRes.status === 'fulfilled') setProjectSummary(projectRes.value);
      if (hrRes.status === 'fulfilled') setHrSummary(hrRes.value);
      if (invRes.status === 'fulfilled') setInventorySummary(invRes.value);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, period]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const getKPILabel = (name: string) => {
    const labels: Record<string, string> = {
      revenue: 'الإيرادات', expenses: 'المصروفات', profit: 'صافي الربح',
      profit_margin: 'هامش الربح', receivables: 'المستحقات', payables: 'المدفوعات',
      active_customers: 'العملاء النشطين', active_projects: 'المشاريع النشطة',
    };
    return labels[name] || name;
  };

  const getKPIFormat = (name: string): 'currency' | 'percent' | 'number' => {
    if (name === 'profit_margin') return 'percent';
    if (['active_customers', 'active_projects'].includes(name)) return 'number';
    return 'currency';
  };

  const getKPIConfig = (name: string) => {
    const configs: Record<string, { gradient: string[]; icon: React.ReactNode }> = {
      revenue: { gradient: GRADIENT_COLORS.primary, icon: <DollarOutlined /> },
      expenses: { gradient: GRADIENT_COLORS.danger, icon: <ShoppingCartOutlined /> },
      profit: { gradient: GRADIENT_COLORS.success, icon: <BankOutlined /> },
      profit_margin: { gradient: GRADIENT_COLORS.info, icon: <RiseOutlined /> },
      receivables: { gradient: GRADIENT_COLORS.warning, icon: <FileTextOutlined /> },
      payables: { gradient: GRADIENT_COLORS.purple, icon: <ShopOutlined /> },
      active_customers: { gradient: GRADIENT_COLORS.success, icon: <TeamOutlined /> },
      active_projects: { gradient: GRADIENT_COLORS.primary, icon: <ProjectOutlined /> },
    };
    return configs[name] || { gradient: GRADIENT_COLORS.primary, icon: <DollarOutlined /> };
  };

  // ─── Greeting ───────────────────────────────────

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'صباح الخير';
    if (hour < 17) return 'مساء الخير';
    return 'مساء الخير';
  };

  const today = new Date().toLocaleDateString('ar-EG', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  // ─── Alerts Section ─────────────────────────────

  const renderAlerts = () => {
    if (alerts.length === 0) return null;
    return (
      <Card
        style={{
          borderRadius: 16, border: 'none',
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          marginBottom: 24,
          background: 'linear-gradient(135deg, #fef3c7 0%, #fef9c3 100%)',
        }}
        bodyStyle={{ padding: '16px 20px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: '#f59e0b20',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#f59e0b', fontSize: 18,
          }}>
            <AlertOutlined />
          </div>
          <div style={{ flex: 1 }}>
            <Text strong style={{ fontSize: 14, color: '#92400e' }}>
              تنبيهات الأعمال
            </Text>
            <Text style={{ fontSize: 12, color: '#a16207', display: 'block' }}>
              {alerts.length} تنبيهات تحتاج انتباهك
            </Text>
          </div>
          <Tag color="#f59e0b" style={{ borderRadius: 20, padding: '2px 12px' }}>
            {alerts.length}
          </Tag>
        </div>
      </Card>
    );
  };

  // ─── Revenue Chart ──────────────────────────────

  const renderRevenueChart = () => {
    if (revenueTrend.length === 0) return <Empty description="لا توجد بيانات" />;
    const data = revenueTrend.map((r) => ({
      ...r,
      label: formatMonth(r.month),
    }));
    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="revenueGradModern" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={formatCurrency} axisLine={false} tickLine={false} />
          <RechartsTooltip
            contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
            formatter={(value: number) => [`${value.toLocaleString()} ج.م`, 'الإيرادات']}
          />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#6366f1"
            strokeWidth={2.5}
            fill="url(#revenueGradModern)"
            dot={false}
            activeDot={{ r: 6, fill: '#6366f1', stroke: '#fff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  // ─── Profit Chart ───────────────────────────────

  const renderProfitChart = () => {
    if (profitTrend.length === 0) return <Empty description="لا توجد بيانات" />;
    const data = profitTrend.map((r) => ({
      ...r,
      label: formatMonth(r.month),
    }));
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={formatCurrency} axisLine={false} tickLine={false} />
          <RechartsTooltip
            contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
            formatter={(value: number, name: string) => [
              `${value.toLocaleString()} ج.م`,
              name === 'revenue' ? 'الإيرادات' : name === 'expenses' ? 'المصروفات' : 'صافي الربح',
            ]}
          />
          <Legend />
          <Bar dataKey="revenue" fill="#6366f1" radius={[6, 6, 0, 0]} name="الإيرادات" />
          <Bar dataKey="expenses" fill="#ef4444" radius={[6, 6, 0, 0]} name="المصروفات" />
          <Bar dataKey="profit" fill="#22c55e" radius={[6, 6, 0, 0]} name="صافي الربح" />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  // ─── Top Customers ──────────────────────────────

  const renderTopCustomers = () => {
    if (topCustomers.length === 0) return <Empty description="لا توجد بيانات" />;
    const maxRevenue = Math.max(...topCustomers.map((c) => c.revenue));
    return (
      <List
        size="small"
        dataSource={topCustomers}
        renderItem={(customer, index) => (
          <List.Item
            style={{ padding: '12px 0', border: 'none' }}
            extra={
              <Text strong style={{ color: '#6366f1', fontSize: 13 }}>
                {customer.revenue.toLocaleString()} ج.م
              </Text>
            }
          >
            <List.Item.Meta
              avatar={
                <Avatar
                  style={{
                    background: CHART_COLORS[index % CHART_COLORS.length],
                    fontWeight: 600, fontSize: 13,
                  }}
                >
                  {index + 1}
                </Avatar>
              }
              title={
                <Text strong style={{ fontSize: 13 }}>
                  {customer.name}
                </Text>
              }
              description={
                <div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {customer.invoices} فاتورة
                  </Text>
                  <Progress
                    percent={Math.round((customer.revenue / maxRevenue) * 100)}
                    strokeColor={CHART_COLORS[index % CHART_COLORS.length]}
                    trailColor="#f0f0f0"
                    showInfo={false}
                    size="small"
                    style={{ marginTop: 4 }}
                  />
                </div>
              }
            />
          </List.Item>
        )}
      />
    );
  };

  // ─── Module Summary ─────────────────────────────

  const renderModuleSummary = () => {
    const modules: Array<{
      title: string; icon: React.ReactNode; color: string;
      stats: Array<{ label: string; value: number; danger?: boolean; warning?: boolean }>;
    }> = [];

    if (projectSummary) {
      modules.push({
        title: 'المشاريع', icon: <ProjectOutlined />, color: '#8b5cf6',
        stats: [
          { label: 'نشط', value: projectSummary.active },
          { label: 'مكتمل', value: projectSummary.completed },
          { label: 'متأخر', value: projectSummary.overdue, danger: projectSummary.overdue > 0 },
        ],
      });
    }
    if (hrSummary) {
      modules.push({
        title: 'الموارد البشرية', icon: <TeamOutlined />, color: '#06b6d4',
        stats: [
          { label: 'موظف', value: hrSummary.total_employees },
          { label: 'قسم', value: hrSummary.departments },
          { label: 'إجازة معلقة', value: hrSummary.pending_leave_requests, warning: hrSummary.pending_leave_requests > 0 },
        ],
      });
    }
    if (inventorySummary) {
      modules.push({
        title: 'المخزون', icon: <ShopOutlined />, color: '#f59e0b',
        stats: [
          { label: 'منتج', value: inventorySummary.total_items },
          { label: 'مخزن', value: inventorySummary.warehouses },
          { label: 'مخزون منخفض', value: inventorySummary.low_stock_items, danger: inventorySummary.low_stock_items > 0 },
        ],
      });
    }

    if (modules.length === 0) return null;

    return (
      <Row gutter={[16, 16]}>
        {modules.map((mod, i) => (
          <Col xs={24} sm={8} key={i}>
            <Card
              style={{
                borderRadius: 16, border: 'none',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
              }}
              bodyStyle={{ padding: 20 }}
              title={
                <Space size={12}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 10,
                    background: `${mod.color}15`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: mod.color, fontSize: 16,
                  }}>
                    {mod.icon}
                  </div>
                  <Text strong style={{ fontSize: 14 }}>{mod.title}</Text>
                </Space>
              }
            >
              <Row gutter={[16, 16]}>
                {mod.stats.map((stat, j) => (
                  <Col span={8} key={j}>
                    <Statistic
                      title={<Text type="secondary" style={{ fontSize: 11 }}>{stat.label}</Text>}
                      value={stat.value}
                      valueStyle={{
                        fontSize: 22, fontWeight: 700,
                        color: stat.danger ? '#ef4444' : stat.warning ? '#f59e0b' : '#1f2937',
                      }}
                    />
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  // ─── Period Selector ────────────────────────────

  const periodLabel: Record<string, string> = {
    today: 'اليوم', yesterday: 'أمس', this_week: 'هذا الأسبوع',
    last_week: 'الأسبوع الماضي', this_month: 'هذا الشهر', last_month: 'الشهر الماضي',
    this_quarter: 'هذا الربع', last_quarter: 'الربع الماضي',
    this_year: 'هذا العام', last_year: 'العام الماضي',
  };

  // ═══════════════════════════════════════════════════
  // Main Render
  // ═══════════════════════════════════════════════════

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* ─── Greeting Header ─── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: 32,
      }}>
        <div>
          <Title level={3} style={{ margin: 0, fontWeight: 700, color: '#1f2937' }}>
            {getGreeting()}، {user?.firstName || 'مدير النظام'} 👋
          </Title>
          <Text type="secondary" style={{ fontSize: 14, marginTop: 4, display: 'block' }}>
            {today} · إليك نظرة عامة على أداء مؤسستك
          </Text>
        </div>
        <Space>
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 160 }}
            options={Object.entries(periodLabel).map(([key, label]) => ({
              value: key, label,
            }))}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchData}
            loading={loading}
            style={{ borderRadius: 10 }}
          >
            تحديث
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {/* ─── Alerts ─── */}
        {renderAlerts()}

        {/* ─── KPI Cards ─── */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {kpis.slice(0, 4).map((kpi) => {
            const config = getKPIConfig(kpi.name);
            return (
              <Col xs={24} sm={12} lg={6} key={kpi.name}>
                <ModernKPICard
                  title={getKPILabel(kpi.name)}
                  value={kpi.current}
                  format={getKPIFormat(kpi.name)}
                  trend={kpi.trend as 'up' | 'down' | 'neutral'}
                  change={kpi.change}
                  icon={config.icon}
                  gradient={config.gradient}
                />
              </Col>
            );
          })}
        </Row>

        {/* ─── Quick Actions ─── */}
        <Card
          style={{
            borderRadius: 16, border: 'none',
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
            marginBottom: 24,
          }}
          bodyStyle={{ padding: 20 }}
          title={
            <Space size={12}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', fontSize: 16,
              }}>
                <ThunderboltOutlined />
              </div>
              <Text strong style={{ fontSize: 15 }}>إجراءات سريعة</Text>
            </Space>
          }
        >
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6} md={4}>
              <QuickAction
                icon={<PlusOutlined />}
                label="عميل جديد"
                color="#6366f1"
                onClick={() => navigate('/sales')}
              />
            </Col>
            <Col xs={12} sm={6} md={4}>
              <QuickAction
                icon={<FileTextOutlined />}
                label="فاتورة جديدة"
                color="#22c55e"
                onClick={() => navigate('/sales')}
              />
            </Col>
            <Col xs={12} sm={6} md={4}>
              <QuickAction
                icon={<ShopOutlined />}
                label="إضافة منتج"
                color="#f59e0b"
                onClick={() => navigate('/inventory')}
              />
            </Col>
            <Col xs={12} sm={6} md={4}>
              <QuickAction
                icon={<ProjectOutlined />}
                label="مشروع جديد"
                color="#8b5cf6"
                onClick={() => navigate('/projects')}
              />
            </Col>
            <Col xs={12} sm={6} md={4}>
              <QuickAction
                icon={<BarChartOutlined />}
                label="التقارير"
                color="#06b6d4"
                onClick={() => navigate('/analytics')}
              />
            </Col>
            <Col xs={12} sm={6} md={4}>
              <QuickAction
                icon={<TeamOutlined />}
                label="الموظفين"
                color="#ec4899"
                onClick={() => navigate('/hr')}
              />
            </Col>
          </Row>
        </Card>

        {/* ─── Charts Row 1: Revenue + Profit ─── */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <ChartCard
              title="تطور الإيرادات"
              icon={<RiseOutlined />}
              extra={<Text type="secondary" style={{ fontSize: 12 }}>آخر 12 شهر</Text>}
            >
              {renderRevenueChart()}
            </ChartCard>
          </Col>
          <Col xs={24} lg={12}>
            <ChartCard
              title="الأرباح والمصروفات"
              icon={<BankOutlined />}
              extra={<Text type="secondary" style={{ fontSize: 12 }}>آخر 12 شهر</Text>}
            >
              {renderProfitChart()}
            </ChartCard>
          </Col>
        </Row>

        {/* ─── Charts Row 2: Top Customers ─── */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} lg={12}>
            <ChartCard
              title="أكبر العملاء"
              icon={<TrophyOutlined />}
              height={280}
              extra={
                <Button type="link" size="small" onClick={() => navigate('/sales')}>
                  عرض الكل
                </Button>
              }
            >
              {renderTopCustomers()}
            </ChartCard>
          </Col>
          <Col xs={24} lg={12}>
            <ChartCard
              title="ملخص الأقسام"
              icon={<ApartmentOutlined />}
              height={280}
            >
              {renderModuleSummary()}
            </ChartCard>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default DashboardPage;
