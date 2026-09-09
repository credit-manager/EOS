/**
 * EOS System — Analytics Deep-Dive Page (P65)
 * Comprehensive analytics with role-based tabs
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Select,
  Spin,
  Tabs,
  Table,
  Statistic,
  Tag,
  List,
  Empty,
  Descriptions,
  Modal,
  Button,
  Progress,
  Badge,
} from 'antd';
import {
  DollarOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  ProjectOutlined,
  ShopOutlined,
  FileTextOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  BankOutlined,
  WarningOutlined,
  ReloadOutlined,
  BarChartOutlined,
  LineChartOutlined,
  FundOutlined,
  UserOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
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
  ExecutiveSummary,
  KPI,
  RevenueTrendPoint,
  ExpensesTrendPoint,
  ProfitTrendPoint,
  CashFlowPoint,
  SalesSummary,
  SalesByPeriod,
  TopCustomer,
  PurchaseSummary,
  TopSupplier,
  InventorySummary,
  StockMovement,
  ProjectSummary,
  ProjectCostItem,
  HRSummary,
  BusinessAlert,
  DrillDownResult,
} from '../types';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const formatCurrency = (v: number) => {
  if (Math.abs(v) >= 1000000) return `${(v / 1000000).toFixed(1)}M`;
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}K`;
  return v.toFixed(0);
};

const formatMonth = (month: string) => {
  const d = new Date(month);
  return d.toLocaleDateString('ar-EG', { month: 'short', year: '2-digit' });
};

const AnalyticsPage: React.FC = () => {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('finance');
  const [period, setPeriod] = useState('this_month');

  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendPoint[]>([]);
  const [expensesTrend, setExpensesTrend] = useState<ExpensesTrendPoint[]>([]);
  const [profitTrend, setProfitTrend] = useState<ProfitTrendPoint[]>([]);
  const [cashFlow, setCashFlow] = useState<CashFlowPoint[]>([]);
  const [salesSummary, setSalesSummary] = useState<SalesSummary | null>(null);
  const [salesPeriods, setSalesPeriods] = useState<SalesByPeriod | null>(null);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [purchaseSummary, setPurchaseSummary] = useState<PurchaseSummary | null>(null);
  const [topSuppliers, setTopSuppliers] = useState<TopSupplier[]>([]);
  const [inventorySummary, setInventorySummary] = useState<InventorySummary | null>(null);
  const [stockMovements, setStockMovements] = useState<StockMovement[]>([]);
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null);
  const [projectCosts, setProjectCosts] = useState<ProjectCostItem[]>([]);
  const [hrSummary, setHrSummary] = useState<HRSummary | null>(null);
  const [alerts, setAlerts] = useState<BusinessAlert[]>([]);

  const [drillDownVisible, setDrillDownVisible] = useState(false);
  const [drillDownData, setDrillDownData] = useState<DrillDownResult | null>(null);
  const [drillDownLoading, setDrillDownLoading] = useState(false);

  const tenantId = user?.tenantId || '';

  const fetchAllData = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        analyticsApi.getExecutiveSummary(tenantId, period),
        analyticsApi.getKPIs(tenantId, period),
        analyticsApi.getRevenueTrend(tenantId, 12),
        analyticsApi.getExpensesTrend(tenantId, 12),
        analyticsApi.getProfitTrend(tenantId, 12),
        analyticsApi.getCashFlow(tenantId, 6),
        analyticsApi.getSalesSummary(tenantId, period),
        analyticsApi.getSalesPeriods(tenantId),
        analyticsApi.getTopCustomers(tenantId, 10),
        analyticsApi.getPurchaseSummary(tenantId, period),
        analyticsApi.getTopSuppliers(tenantId, 10),
        analyticsApi.getInventorySummary(tenantId),
        analyticsApi.getStockMovements(tenantId, 30),
        analyticsApi.getProjectSummary(tenantId),
        analyticsApi.getProjectCosts(tenantId),
        analyticsApi.getHRSummary(tenantId),
        analyticsApi.getAlerts(tenantId),
      ]);

      const set = (i: number, setter: (v: any) => void, key?: string) => {
        if (results[i].status === 'fulfilled') {
          setter(key ? (results[i] as any).value[key] : (results[i] as any).value);
        }
      };

      set(0, setSummary);
      set(1, setKpis, 'kpis');
      set(2, setRevenueTrend, 'trend');
      set(3, setExpensesTrend, 'trend');
      set(4, setProfitTrend, 'trend');
      set(5, setCashFlow, 'cash_flow');
      set(6, setSalesSummary);
      set(7, setSalesPeriods);
      set(8, setTopCustomers, 'customers');
      set(9, setPurchaseSummary);
      set(10, setTopSuppliers, 'suppliers');
      set(11, setInventorySummary);
      set(12, setStockMovements, 'movements');
      set(13, setProjectSummary);
      set(14, setProjectCosts, 'projects');
      set(15, setHrSummary);
      set(16, setAlerts, 'alerts');
    } catch (err) {
      console.error('Analytics fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, period]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  const handleDrillDown = async (entityType: string, entityId: string) => {
    if (!tenantId) return;
    setDrillDownLoading(true);
    setDrillDownVisible(true);
    try {
      const result = await analyticsApi.getDrillDown(tenantId, entityType, entityId);
      setDrillDownData(result);
    } catch {
      setDrillDownData(null);
    } finally {
      setDrillDownLoading(false);
    }
  };

  const renderKPITabs = () => (
    <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
      {kpis.map((kpi) => {
        const color = kpi.trend === 'up' ? '#52c41a' : kpi.trend === 'down' ? '#ff4d4f' : '#8c8c8c';
        return (
          <Col xs={12} sm={6} lg={3} key={kpi.name}>
            <Card size="small" bodyStyle={{ padding: 16 }}>
              <Statistic
                title={<Text type="secondary" style={{ fontSize: 11 }}>{kpi.name}</Text>}
                value={kpi.current}
                prefix={kpi.format === 'currency' ? 'ج.م' : undefined}
                suffix={kpi.format === 'percent' ? '%' : undefined}
                precision={kpi.format === 'percent' ? 1 : 0}
                valueStyle={{ fontSize: 18, fontWeight: 700, color }}
              />
              <Tag
                color={kpi.trend === 'up' ? 'green' : kpi.trend === 'down' ? 'red' : 'default'}
                style={{ marginTop: 4 }}
              >
                {kpi.trend === 'up' ? <ArrowUpOutlined /> : kpi.trend === 'down' ? <ArrowDownOutlined /> : null}
                {' '}{Math.abs(kpi.change)}%
              </Tag>
            </Card>
          </Col>
        );
      })}
    </Row>
  );

  const renderFinanceTab = () => (
    <Row gutter={[16, 16]}>
      {/* Revenue Trend */}
      <Col xs={24} lg={12}>
        <Card title={<Space><LineChartOutlined /> تطور الإيرادات</Space>}>
          {revenueTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={revenueTrend.map(r => ({ ...r, label: formatMonth(r.month) }))}>
                <defs>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1890ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#1890ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={formatCurrency} />
                <RechartsTooltip formatter={(v: number) => [`${v.toLocaleString()} ج.م`, 'الإيرادات']} />
                <Area type="monotone" dataKey="revenue" stroke="#1890ff" fill="url(#revGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>
      </Col>

      {/* Expenses Trend */}
      <Col xs={24} lg={12}>
        <Card title={<Space><BarChartOutlined /> تطور المصروفات</Space>}>
          {expensesTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={expensesTrend.map(r => ({ ...r, label: formatMonth(r.month) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={formatCurrency} />
                <RechartsTooltip formatter={(v: number) => [`${v.toLocaleString()} ج.م`, 'المصروفات']} />
                <Bar dataKey="expenses" fill="#ff4d4f" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>
      </Col>

      {/* Profit Trend */}
      <Col xs={24} lg={12}>
        <Card title={<Space><FundOutlined /> صافي الربح</Space>}>
          {profitTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={profitTrend.map(r => ({ ...r, label: formatMonth(r.month) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={formatCurrency} />
                <RechartsTooltip formatter={(v: number, name: string) => [
                  `${v.toLocaleString()} ج.م`,
                  name === 'revenue' ? 'الإيرادات' : name === 'expenses' ? 'المصروفات' : 'صافي الربح',
                ]} />
                <Legend />
                <Line type="monotone" dataKey="revenue" stroke="#1890ff" strokeWidth={2} dot={false} name="الإيرادات" />
                <Line type="monotone" dataKey="expenses" stroke="#ff4d4f" strokeWidth={2} dot={false} name="المصروفات" />
                <Line type="monotone" dataKey="profit" stroke="#52c41a" strokeWidth={2} dot={false} name="صافي الربح" />
              </LineChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>
      </Col>

      {/* Cash Flow */}
      <Col xs={24} lg={12}>
        <Card title={<Space><DollarOutlined /> التدفقات النقدية</Space>}>
          {cashFlow.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={cashFlow.map(r => ({ ...r, label: formatMonth(r.month) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={formatCurrency} />
                <RechartsTooltip formatter={(v: number, name: string) => [
                  `${v.toLocaleString()} ج.م`,
                  name === 'inflow' ? 'الوارد' : name === 'outflow' ? 'الصادر' : 'الصافي',
                ]} />
                <Legend />
                <Bar dataKey="inflow" fill="#52c41a" name="الوارد" radius={[4, 4, 0, 0]} />
                <Bar dataKey="outflow" fill="#ff4d4f" name="الصادر" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>
      </Col>

      {/* Summary Cards */}
      {summary && (
        <Col span={24}>
          <Card title="ملخص تنفيذي">
            <Row gutter={[24, 16]}>
              <Col xs={12} sm={6}>
                <Statistic
                  title="الإيرادات"
                  value={summary.revenue}
                  prefix="ج.م"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="المصروفات"
                  value={summary.expenses}
                  prefix="ج.م"
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="صافي الربح"
                  value={summary.profit}
                  prefix="ج.م"
                  valueStyle={{ color: summary.profit >= 0 ? '#52c41a' : '#ff4d4f' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="هامش الربح"
                  value={summary.profit_margin}
                  suffix="%"
                  valueStyle={{ color: summary.profit_margin >= 0 ? '#52c41a' : '#ff4d4f' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="المستحقات"
                  value={summary.receivables}
                  prefix="ج.م"
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="المدفوعات"
                  value={summary.payables}
                  prefix="ج.م"
                  valueStyle={{ color: '#722ed1' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="المركز النقدي"
                  value={summary.cash_position}
                  prefix="ج.م"
                  valueStyle={{ color: summary.cash_position >= 0 ? '#52c41a' : '#ff4d4f' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="العملاء"
                  value={summary.active_customers}
                  prefix={<TeamOutlined />}
                  valueStyle={{ color: '#13c2c2' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      )}
    </Row>
  );

  const renderSalesTab = () => (
    <Row gutter={[16, 16]}>
      {/* Sales Summary */}
      <Col xs={24} sm={12} lg={6}>
        <Card size="small">
          <Statistic title="إجمالي الفواتير" value={salesSummary?.total_invoices || 0} prefix={<FileTextOutlined />} />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <Card size="small">
          <Statistic title="إجمالي الإيرادات" value={salesSummary?.total_revenue || 0} prefix="ج.م" valueStyle={{ color: '#1890ff' }} />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <Card size="small">
          <Statistic title="متوسط الفاتورة" value={salesSummary?.average_invoice || 0} prefix="ج.م" valueStyle={{ color: '#52c41a' }} />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <Card size="small">
          <Statistic title="نسبة التحصيل" value={salesSummary?.collection_rate || 0} suffix="%" valueStyle={{ color: '#722ed1' }} />
        </Card>
      </Col>

      {/* Period Comparison */}
      {salesPeriods && (
        <Col span={24}>
          <Card title="مقارنة الفترات">
            <Row gutter={[24, 16]}>
              <Col xs={24} md={8}>
                <Card type="inner" title="هذا الشهر" size="small">
                  <Statistic title="الإيرادات" value={salesPeriods.this_month.total_revenue} prefix="ج.م" />
                  <Statistic title="الفواتير" value={salesPeriods.this_month.total_invoices} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card type="inner" title="الشهر الماضي" size="small">
                  <Statistic title="الإيرادات" value={salesPeriods.last_month.total_revenue} prefix="ج.م" />
                  <Statistic title="الفواتير" value={salesPeriods.last_month.total_invoices} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card type="inner" title="هذا العام" size="small">
                  <Statistic title="الإيرادات" value={salesPeriods.this_year.total_revenue} prefix="ج.م" />
                  <Statistic title="الفواتير" value={salesPeriods.this_year.total_invoices} />
                </Card>
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={12}>
                <Statistic
                  title="التغيير في الإيرادات"
                  value={salesPeriods.changes.revenue_change}
                  suffix="%"
                  prefix={salesPeriods.changes.revenue_change >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                  valueStyle={{ color: salesPeriods.changes.revenue_change >= 0 ? '#52c41a' : '#ff4d4f' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="التغيير في الفواتير"
                  value={salesPeriods.changes.invoice_change}
                  suffix="%"
                  prefix={salesPeriods.changes.invoice_change >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                  valueStyle={{ color: salesPeriods.changes.invoice_change >= 0 ? '#52c41a' : '#ff4d4f' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      )}

      {/* Top Customers */}
      <Col xs={24} lg={12}>
        <Card title={<Space><TeamOutlined /> أكبر العملاء</Space>}>
          {topCustomers.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topCustomers.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={formatCurrency} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={100} />
                <RechartsTooltip formatter={(v: number) => [`${v.toLocaleString()} ج.م`, 'الإيرادات']} />
                <Bar dataKey="revenue" fill="#1890ff" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>
      </Col>

      {/* Purchases */}
      <Col xs={24} lg={12}>
        <Card title={<Space><ShoppingCartOutlined /> المشتريات</Space>}>
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Statistic title="إجمالي الطلبات" value={purchaseSummary?.total_orders || 0} />
            </Col>
            <Col span={12}>
              <Statistic title="المبلغ الإجمالي" value={purchaseSummary?.total_amount || 0} prefix="ج.م" />
            </Col>
            <Col span={12}>
              <Statistic title="طلبات معلقة" value={purchaseSummary?.pending_orders || 0} valueStyle={{ color: '#faad14' }} />
            </Col>
            <Col span={12}>
              <Statistic title="نسبة الموافقة" value={purchaseSummary?.approval_rate || 0} suffix="%" />
            </Col>
          </Row>
          {topSuppliers.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Text strong>أكبر الموردين:</Text>
              <List
                size="small"
                dataSource={topSuppliers.slice(0, 5)}
                renderItem={(s) => (
                  <List.Item>
                    <Text>{s.name}</Text>
                    <Text type="secondary">{s.purchases.toLocaleString()} ج.م ({s.orders} طلب)</Text>
                  </List.Item>
                )}
              />
            </div>
          )}
        </Card>
      </Col>
    </Row>
  );

  const renderProjectsTab = () => (
    <Row gutter={[16, 16]}>
      {projectSummary && (
        <>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="إجمالي المشاريع" value={projectSummary.total_projects} prefix={<ProjectOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="نشط" value={projectSummary.active} valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="مكتمل" value={projectSummary.completed} valueStyle={{ color: '#1890ff' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="متأخر" value={projectSummary.overdue} valueStyle={{ color: '#ff4d4f' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12}>
            <Card size="small">
              <Statistic title="الميزانية الإجمالية" value={projectSummary.total_budget} prefix="ج.م" />
              <Progress
                percent={Math.min(projectSummary.budget_utilization, 100)}
                status={projectSummary.budget_utilization > 100 ? 'exception' : 'active'}
                format={() => `${projectSummary.budget_utilization}%`}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>استغلال الميزانية</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12}>
            <Card size="small">
              <Statistic title="المصروفات الفعلية" value={projectSummary.total_spent} prefix="ج.م" valueStyle={{ color: '#ff4d4f' }} />
            </Card>
          </Col>
        </>
      )}

      {/* Project Cost Breakdown */}
      <Col span={24}>
        <Card title={<Space><BarChartOutlined /> تكلفة المشاريع</Space>}>
          {projectCosts.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={projectCosts.slice(0, 10)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={formatCurrency} />
                  <RechartsTooltip formatter={(v: number, name: string) => [
                    `${v.toLocaleString()} ج.م`,
                    name === 'budget' ? 'الميزانية' : name === 'actual_cost' ? 'التكلفة الفعلية' : 'تكلفة العمالة',
                  ]} />
                  <Legend />
                  <Bar dataKey="budget" fill="#1890ff" name="الميزانية" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="actual_cost" fill="#ff4d4f" name="التكلفة الفعلية" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="labor_cost" fill="#52c41a" name="تكلفة العمالة" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <Table
                size="small"
                dataSource={projectCosts}
                rowKey="project_id"
                pagination={false}
                onRow={(record) => ({
                  onClick: () => handleDrillDown('project', record.project_id),
                  style: { cursor: 'pointer' },
                })}
                columns={[
                  { title: 'المشروع', dataIndex: 'name', key: 'name' },
                  { title: 'الميزانية', dataIndex: 'budget', key: 'budget', render: (v: number) => `${v.toLocaleString()} ج.م` },
                  { title: 'الفعلي', dataIndex: 'actual_cost', key: 'actual_cost', render: (v: number) => `${v.toLocaleString()} ج.م` },
                  {
                    title: 'الانحراف', dataIndex: 'variance', key: 'variance',
                    render: (v: number) => (
                      <Tag color={v >= 0 ? 'green' : 'red'}>
                        {v >= 0 ? '+' : ''}{v.toLocaleString()} ج.م
                      </Tag>
                    ),
                  },
                  {
                    title: 'الحالة', dataIndex: 'status', key: 'status',
                    render: (s: string) => (
                      <Tag color={s === 'completed' ? 'green' : s === 'in_progress' ? 'blue' : 'default'}>{s}</Tag>
                    ),
                  },
                ]}
              />
            </>
          ) : <Empty description="لا توجد بيانات مشاريع" />}
        </Card>
      </Col>
    </Row>
  );

  const renderHRTab = () => (
    <Row gutter={[16, 16]}>
      {hrSummary && (
        <>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="الموظفون النشطون" value={hrSummary.total_employees} prefix={<UserOutlined />} valueStyle={{ color: '#1890ff' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="الأقسام" value={hrSummary.departments} prefix={<ApartmentOutlined />} valueStyle={{ color: '#722ed1' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="إجمالي الرواتب" value={hrSummary.total_payroll} prefix="ج.م" valueStyle={{ color: '#ff4d4f' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="إجازات معلقة" value={hrSummary.pending_leave_requests} valueStyle={{ color: '#faad14' }} />
            </Card>
          </Col>

          {/* HR Overview Chart */}
          <Col span={24}>
            <Card title="نظرة عامة على الموارد البشرية">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[
                  { name: 'الموظفون', value: hrSummary.total_employees },
                  { name: 'الأقسام', value: hrSummary.departments },
                  { name: 'إجازات معلقة', value: hrSummary.pending_leave_requests },
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <RechartsTooltip />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {[
                      <Cell key="emp" fill="#1890ff" />,
                      <Cell key="dept" fill="#722ed1" />,
                      <Cell key="leave" fill="#faad14" />,
                    ]}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </>
      )}
    </Row>
  );

  const renderInventoryTab = () => (
    <Row gutter={[16, 16]}>
      {inventorySummary && (
        <>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="إجمالي المنتجات" value={inventorySummary.total_items} prefix={<ShopOutlined />} valueStyle={{ color: '#1890ff' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="قيمة المخزون" value={inventorySummary.total_stock_value} prefix="ج.م" valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="مخزون منخفض" value={inventorySummary.low_stock_items} valueStyle={{ color: '#ff4d4f' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="المخازن" value={inventorySummary.warehouses} valueStyle={{ color: '#722ed1' }} />
            </Card>
          </Col>
        </>
      )}

      {/* Stock Movements */}
      <Col span={24}>
        <Card title={<Space><BarChartOutlined /> حركة المخزون (آخر 30 يوم)</Space>}>
          {stockMovements.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stockMovements.map(m => ({ ...m, label: m.date }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <RechartsTooltip />
                <Legend />
                <Bar dataKey="in" fill="#52c41a" name="وارد" radius={[4, 4, 0, 0]} />
                <Bar dataKey="out" fill="#ff4d4f" name="صادر" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty description="لا توجد حركات مخزون" />}
        </Card>
      </Col>
    </Row>
  );

  const renderAlertsTab = () => (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card title={<Space><WarningOutlined style={{ color: '#faad14' }} /> تنبيهات الأعمال</Space>}>
          {alerts.length > 0 ? (
            <List
              dataSource={alerts}
              renderItem={(alert) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <div style={{
                        width: 40, height: 40, borderRadius: 8,
                        background: alert.type === 'danger' ? '#fff1f0' : '#fffbe6',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <WarningOutlined style={{
                          color: alert.type === 'danger' ? '#ff4d4f' : '#faad14',
                          fontSize: 20,
                        }} />
                      </div>
                    }
                    title={
                      <Space>
                        <Text strong>{alert.title}</Text>
                        <Tag color={alert.type === 'danger' ? 'red' : 'orange'}>{alert.category}</Tag>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={2}>
                        <Text type="secondary">{alert.message}</Text>
                        <Text style={{ color: '#1890ff', fontSize: 12 }}>{alert.action}</Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="لا توجد تنبيهات" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </Col>
    </Row>
  );

  const renderDrillDownModal = () => (
    <Modal
      title="تفاصيل المستند"
      open={drillDownVisible}
      onCancel={() => { setDrillDownVisible(false); setDrillDownData(null); }}
      footer={null}
      width={700}
    >
      {drillDownLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
      ) : drillDownData ? (
        <Descriptions bordered column={2} size="small">
          {Object.entries(drillDownData).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {typeof value === 'number' ? value.toLocaleString() : String(value ?? '-')}
            </Descriptions.Item>
          ))}
        </Descriptions>
      ) : <Empty description="لا توجد بيانات" />}
    </Modal>
  );

  const periodOptions = [
    { value: 'today', label: 'اليوم' },
    { value: 'this_week', label: 'هذا الأسبوع' },
    { value: 'this_month', label: 'هذا الشهر' },
    { value: 'last_month', label: 'الشهر الماضي' },
    { value: 'this_quarter', label: 'هذا الربع' },
    { value: 'this_year', label: 'هذا العام' },
  ];

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>التحليلات المتقدمة</Title>
          <Tag color="blue">P65</Tag>
        </Space>
        <Space>
          <Select value={period} onChange={setPeriod} style={{ width: 160 }} options={periodOptions} />
          <Button icon={<ReloadOutlined />} onClick={fetchAllData} loading={loading}>تحديث</Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {/* KPIs */}
        {renderKPITabs()}

        {/* Tabs */}
        <Tabs activeKey={activeTab} onChange={setActiveTab} type="card" size="large">
          <TabPane tab={<Space><BankOutlined /> المالية</Space>} key="finance">
            {renderFinanceTab()}
          </TabPane>
          <TabPane tab={<Space><ShoppingCartOutlined /> المبيعات والمشتريات</Space>} key="sales">
            {renderSalesTab()}
          </TabPane>
          <TabPane tab={<Space><ProjectOutlined /> المشاريع</Space>} key="projects">
            {renderProjectsTab()}
          </TabPane>
          <TabPane tab={<Space><TeamOutlined /> الموارد البشرية</Space>} key="hr">
            {renderHRTab()}
          </TabPane>
          <TabPane tab={<Space><ShopOutlined /> المخزون</Space>} key="inventory">
            {renderInventoryTab()}
          </TabPane>
          <TabPane tab={
            <Space>
              <WarningOutlined />
              التنبيهات
              {alerts.length > 0 && <Badge count={alerts.length} size="small" />}
            </Space>
          } key="alerts">
            {renderAlertsTab()}
          </TabPane>
        </Tabs>
      </Spin>

      {renderDrillDownModal()}
    </div>
  );
};

export default AnalyticsPage;
