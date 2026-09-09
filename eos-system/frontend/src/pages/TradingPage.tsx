/**
 * Trading ERP Professional — Workspace
 * Dashboard → Sales → Purchasing → Inventory → Customers → Suppliers → Pricing
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Typography, Space, Spin, Button, Tag, Table, Statistic,
  Tabs, Modal, Form, Input, Select, message, InputNumber, Empty,
  Divider, Alert,
} from 'antd';
import {
  ShopOutlined, ShoppingCartOutlined, TeamOutlined, CarOutlined,
  PlusOutlined, ReloadOutlined, WarningOutlined,
  DollarOutlined, ImportOutlined, ExportOutlined, DatabaseOutlined,
  InboxOutlined, PercentageOutlined, DashboardOutlined,
} from '@ant-design/icons';
import apiClient from '../services/apiClient';

const { Text } = Typography;

/* ═══════════════════════════════════════════════════
   API Client
   ═══════════════════════════════════════════════════ */

const api = {
  dashboard: () => apiClient.get('/trading/dashboard'),
  // Items
  items: (p?: any) => apiClient.get('/trading/items', { params: p }),
  createItem: (d: any) => apiClient.post('/trading/items', d),
  updateItem: (id: string, d: any) => apiClient.put(`/trading/items/${id}`, d),
  // Warehouses
  warehouses: () => apiClient.get('/trading/warehouses'),
  createWarehouse: (d: any) => apiClient.post('/trading/warehouses', d),
  // Customers
  customers: (p?: any) => apiClient.get('/trading/customers', { params: p }),
  createCustomer: (d: any) => apiClient.post('/trading/customers', d),
  updateCustomer: (id: string, d: any) => apiClient.put(`/trading/customers/${id}`, d),
  // Suppliers
  suppliers: (p?: any) => apiClient.get('/trading/suppliers', { params: p }),
  createSupplier: (d: any) => apiClient.post('/trading/suppliers', d),
  updateSupplier: (id: string, d: any) => apiClient.put(`/trading/suppliers/${id}`, d),
  // Sales
  quotations: () => apiClient.get('/trading/quotations'),
  createQuotation: (d: any) => apiClient.post('/trading/quotations', d),
  salesOrders: () => apiClient.get('/trading/sales-orders'),
  createSalesOrder: (d: any) => apiClient.post('/trading/sales-orders', d),
  deliveries: () => apiClient.get('/trading/deliveries'),
  createDelivery: (d: any) => apiClient.post('/trading/deliveries', d),
  salesInvoices: () => apiClient.get('/trading/sales-invoices'),
  createSalesInvoice: (d: any) => apiClient.post('/trading/sales-invoices', d),
  customerPayments: () => apiClient.get('/trading/customer-payments'),
  createCustomerPayment: (d: any) => apiClient.post('/trading/customer-payments', d),
  // Purchases
  purchaseRequests: () => apiClient.get('/trading/purchase-requests'),
  createPR: (d: any) => apiClient.post('/trading/purchase-requests', d),
  approvePR: (id: string) => apiClient.put(`/trading/purchase-requests/${id}/approve`),
  purchaseOrders: () => apiClient.get('/trading/purchase-orders'),
  createPO: (d: any) => apiClient.post('/trading/purchase-orders', d),
  grn: () => apiClient.get('/trading/grn'),
  createGRN: (d: any) => apiClient.post('/trading/grn', d),
  purchaseInvoices: () => apiClient.get('/trading/purchase-invoices'),
  createPurchaseInvoice: (d: any) => apiClient.post('/trading/purchase-invoices', d),
  supplierPayments: () => apiClient.get('/trading/supplier-payments'),
  createSupplierPayment: (d: any) => apiClient.post('/trading/supplier-payments', d),
  // Stock
  stock: (p?: any) => apiClient.get('/trading/stock', { params: p }),
  createTransfer: (d: any) => apiClient.post('/trading/stock-transfers', d),
  // Price Lists
  priceLists: () => apiClient.get('/trading/price-lists'),
  createPriceList: (d: any) => apiClient.post('/trading/price-lists', d),
  // Audit
  audit: (p?: any) => apiClient.get('/trading/audit', { params: p }),
};

/* ═══════════════════════════════════════════════════
   Shared Components
   ═══════════════════════════════════════════════════ */

const KpiCard = ({ title, value, icon, color, suffix, sub }: any) => (
  <div style={{
    background: '#fff', borderRadius: 14, padding: '20px 22px',
    border: '1px solid #f0f0f0', position: 'relative', overflow: 'hidden',
  }}>
    <div style={{
      position: 'absolute', top: -20, right: -20, width: 80, height: 80,
      borderRadius: '50%', background: `${color}08`,
    }} />
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <Text type="secondary" style={{ fontSize: 13 }}>{title}</Text>
        <div style={{ fontSize: 26, fontWeight: 700, color: '#1a1a2e', marginTop: 4 }}>
          {value}{suffix && <span style={{ fontSize: 14, color: '#888', marginLeft: 4 }}>{suffix}</span>}
        </div>
        {sub && <Text type="secondary" style={{ fontSize: 12 }}>{sub}</Text>}
      </div>
      <div style={{
        width: 44, height: 44, borderRadius: 12, display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        background: `${color}10`, color, fontSize: 20,
      }}>
        {icon}
      </div>
    </div>
  </div>
);

const statusColor: Record<string, string> = {
  draft: 'default', pending: 'processing', sent: 'blue',
  accepted: 'green', approved: 'green', delivered: 'green',
  received: 'green', paid: 'green', partial: 'orange',
  rejected: 'red', cancelled: 'red', unpaid: 'orange',
  uninvoiced: 'default', invoiced: 'blue',
};

const fmt = (n: number) => n?.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) || '0';
const fmtEgp = (n: number) => `EGP ${fmt(n)}`;

/* ═══════════════════════════════════════════════════
   DASHBOARD TAB
   ═══════════════════════════════════════════════════ */

const DashboardTab = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r: any = await api.dashboard();
      setData(r.data?.data || r.data);
    } catch { message.error('Failed to load dashboard'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!data) return <Empty />;

  const d = data;
  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Sales This Month" value={fmtEgp(d.sales?.total)}
            icon={<ShopOutlined />} color="#1890ff" sub={`${d.sales?.count || 0} orders`} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Purchases This Month" value={fmtEgp(d.purchases?.total)}
            icon={<ShoppingCartOutlined />} color="#722ed1" sub={`${d.purchases?.count || 0} orders`} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Receivables" value={fmtEgp(d.receivables?.total)}
            icon={<ImportOutlined />} color="#f5222d" sub={`${d.receivables?.count || 0} unpaid`} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Payables" value={fmtEgp(d.payables?.total)}
            icon={<ExportOutlined />} color="#fa8c16" sub={`${d.payables?.count || 0} unpaid`} />
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Stock Value" value={fmtEgp(d.stock?.value)}
            icon={<DatabaseOutlined />} color="#52c41a" sub={`${d.stock?.items || 0} items`} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Low Stock Alerts" value={d.low_stock_alerts || 0}
            icon={<WarningOutlined />} color="#faad14" sub="Items below reorder" />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Total Items" value={d.total_items || 0}
            icon={<InboxOutlined />} color="#13c2c2" />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <KpiCard title="Total Customers" value={d.total_customers || 0}
            icon={<TeamOutlined />} color="#eb2f96" />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} md={12}>
          <Card title="Sales vs Purchases" size="small">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="Sales" value={d.sales?.total || 0} precision={0}
                  valueStyle={{ color: '#1890ff' }} prefix={<ShopOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="Purchases" value={d.purchases?.total || 0} precision={0}
                  valueStyle={{ color: '#722ed1' }} prefix={<ShoppingCartOutlined />} />
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="Net Margin" value={(d.sales?.total || 0) - (d.purchases?.total || 0)}
                  precision={0} valueStyle={{ color: '#52c41a' }} prefix={<DollarOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="Margin %" value={
                  d.sales?.total ? (((d.sales?.total - d.purchases?.total) / d.sales?.total) * 100).toFixed(1) : 0
                } suffix="%" valueStyle={{ color: '#52c41a' }} />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Cash Position" size="small">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="Inflow (Collections)" value={d.receivables?.total || 0} precision={0}
                  valueStyle={{ color: '#52c41a' }} prefix={<ImportOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="Outflow (Payments)" value={d.payables?.total || 0} precision={0}
                  valueStyle={{ color: '#f5222d' }} prefix={<ExportOutlined />} />
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="Receivables" value={d.receivables?.count || 0}
                  suffix="invoices" valueStyle={{ fontSize: 16 }} />
              </Col>
              <Col span={12}>
                <Statistic title="Payables" value={d.payables?.count || 0}
                  suffix="invoices" valueStyle={{ fontSize: 16 }} />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {d.low_stock_alerts > 0 && (
        <Alert
          message={`${d.low_stock_alerts} items are below reorder point. Consider restocking.`}
          type="warning" showIcon style={{ marginTop: 16 }}
        />
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   SALES TAB
   ═══════════════════════════════════════════════════ */

const SalesTab = () => {
  const [tab, setTab] = useState('orders');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      let r: any;
      switch (tab) {
        case 'orders': r = await api.salesOrders(); break;
        case 'invoices': r = await api.salesInvoices(); break;
        case 'payments': r = await api.customerPayments(); break;
        case 'quotations': r = await api.quotations(); break;
        default: r = await api.salesOrders();
      }
      setData(r.data?.data || r.data || []);
    } catch { message.error('Failed to load'); }
    setLoading(false);
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const columns: any[] = tab === 'orders' ? [
    { title: 'SO Number', dataIndex: 'so_number', key: 'so_number',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Customer', dataIndex: 'customer_id', key: 'customer', ellipsis: true },
    { title: 'Date', dataIndex: 'order_date', key: 'date' },
    { title: 'Total', dataIndex: 'total', key: 'total', render: (v: number) => fmtEgp(v) },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColor[v]}>{v?.toUpperCase()}</Tag> },
    { title: 'Delivery', dataIndex: 'delivery_status', key: 'ds',
      render: (v: string) => <Tag color={statusColor[v]}>{v}</Tag> },
    { title: 'Invoice', dataIndex: 'invoice_status', key: 'is',
      render: (v: string) => <Tag color={statusColor[v]}>{v}</Tag> },
  ] : tab === 'invoices' ? [
    { title: 'Invoice #', dataIndex: 'invoice_number', key: 'inv',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Customer', dataIndex: 'customer_id', key: 'customer', ellipsis: true },
    { title: 'Date', dataIndex: 'invoice_date', key: 'date' },
    { title: 'Total', dataIndex: 'total', key: 'total', render: (v: number) => fmtEgp(v) },
    { title: 'Paid', dataIndex: 'paid_amount', key: 'paid', render: (v: number) => fmtEgp(v) },
    { title: 'Balance', dataIndex: 'balance', key: 'bal',
      render: (v: number) => <Text type={v > 0 ? 'danger' : 'success'}>{fmtEgp(v)}</Text> },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColor[v]}>{v?.toUpperCase()}</Tag> },
  ] : tab === 'payments' ? [
    { title: 'Payment #', dataIndex: 'payment_number', key: 'pay',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Customer', dataIndex: 'customer_id', key: 'customer', ellipsis: true },
    { title: 'Date', dataIndex: 'payment_date', key: 'date' },
    { title: 'Amount', dataIndex: 'amount', key: 'amount', render: (v: number) => fmtEgp(v) },
    { title: 'Method', dataIndex: 'payment_method', key: 'method',
      render: (v: string) => <Tag>{v}</Tag> },
  ] : [
    { title: 'Quote #', dataIndex: 'quote_number', key: 'qt',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Customer', dataIndex: 'customer_id', key: 'customer', ellipsis: true },
    { title: 'Date', dataIndex: 'quote_date', key: 'date' },
    { title: 'Total', dataIndex: 'total', key: 'total', render: (v: number) => fmtEgp(v) },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColor[v]}>{v?.toUpperCase()}</Tag> },
  ];

  return (
    <div>
      <Tabs activeKey={tab} onChange={setTab} items={[
        { key: 'orders', label: `Sales Orders (${data.length})` },
        { key: 'invoices', label: 'Invoices' },
        { key: 'payments', label: 'Collections' },
        { key: 'quotations', label: 'Quotations' },
      ]} />
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
      </div>
      <Table dataSource={data} columns={columns} rowKey="id" size="small"
        loading={loading} pagination={{ pageSize: 20 }}
        summary={() => {
          if (tab === 'invoices' && data.length) {
            const totalBal = data.reduce((s: number, r: any) => s + (r.balance || 0), 0);
            return (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={5}><strong>Outstanding</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={5}>
                  <Text type="danger" strong>{fmtEgp(totalBal)}</Text>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            );
          }
          return null;
        }} />
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   PURCHASING TAB
   ═══════════════════════════════════════════════════ */

const PurchasingTab = () => {
  const [tab, setTab] = useState('orders');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      let r: any;
      switch (tab) {
        case 'orders': r = await api.purchaseOrders(); break;
        case 'invoices': r = await api.purchaseInvoices(); break;
        case 'payments': r = await api.supplierPayments(); break;
        case 'requests': r = await api.purchaseRequests(); break;
        case 'grn': r = await api.grn(); break;
        default: r = await api.purchaseOrders();
      }
      setData(r.data?.data || r.data || []);
    } catch { message.error('Failed to load'); }
    setLoading(false);
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const columns: any[] = tab === 'orders' ? [
    { title: 'PO Number', dataIndex: 'po_number', key: 'po',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Supplier', dataIndex: 'supplier_id', key: 'sup', ellipsis: true },
    { title: 'Date', dataIndex: 'order_date', key: 'date' },
    { title: 'Total', dataIndex: 'total', key: 'total', render: (v: number) => fmtEgp(v) },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColor[v]}>{v?.toUpperCase()}</Tag> },
    { title: 'GRN', dataIndex: 'grn_status', key: 'grn',
      render: (v: string) => <Tag color={statusColor[v]}>{v}</Tag> },
    { title: 'Invoice', dataIndex: 'invoice_status', key: 'inv',
      render: (v: string) => <Tag color={statusColor[v]}>{v}</Tag> },
  ] : tab === 'invoices' ? [
    { title: 'Invoice #', dataIndex: 'invoice_number', key: 'inv',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Supplier', dataIndex: 'supplier_id', key: 'sup', ellipsis: true },
    { title: 'Date', dataIndex: 'invoice_date', key: 'date' },
    { title: 'Total', dataIndex: 'total', key: 'total', render: (v: number) => fmtEgp(v) },
    { title: 'Paid', dataIndex: 'paid_amount', key: 'paid', render: (v: number) => fmtEgp(v) },
    { title: 'Balance', dataIndex: 'balance', key: 'bal',
      render: (v: number) => <Text type={v > 0 ? 'danger' : 'success'}>{fmtEgp(v)}</Text> },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColor[v]}>{v?.toUpperCase()}</Tag> },
  ] : tab === 'payments' ? [
    { title: 'Payment #', dataIndex: 'payment_number', key: 'pay',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Supplier', dataIndex: 'supplier_id', key: 'sup', ellipsis: true },
    { title: 'Date', dataIndex: 'payment_date', key: 'date' },
    { title: 'Amount', dataIndex: 'amount', key: 'amount', render: (v: number) => fmtEgp(v) },
    { title: 'Method', dataIndex: 'payment_method', key: 'method',
      render: (v: string) => <Tag>{v}</Tag> },
  ] : tab === 'requests' ? [
    { title: 'PR Number', dataIndex: 'pr_number', key: 'pr',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Requested By', dataIndex: 'requested_by', key: 'by' },
    { title: 'Date', dataIndex: 'request_date', key: 'date' },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColor[v]}>{v?.toUpperCase()}</Tag> },
  ] : [
    { title: 'GRN #', dataIndex: 'grn_number', key: 'grn',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'PO', dataIndex: 'po_id', key: 'po', ellipsis: true },
    { title: 'Date', dataIndex: 'grn_date', key: 'date' },
    { title: 'Received By', dataIndex: 'received_by', key: 'by' },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={statusColor[v]}>{v?.toUpperCase()}</Tag> },
  ];

  return (
    <div>
      <Tabs activeKey={tab} onChange={setTab} items={[
        { key: 'orders', label: `Purchase Orders (${data.length})` },
        { key: 'grn', label: 'GRN' },
        { key: 'invoices', label: 'Invoices' },
        { key: 'payments', label: 'Payments' },
        { key: 'requests', label: 'Requests' },
      ]} />
      <Button icon={<ReloadOutlined />} onClick={load} style={{ marginBottom: 12 }}>Refresh</Button>
      <Table dataSource={data} columns={columns} rowKey="id" size="small"
        loading={loading} pagination={{ pageSize: 20 }} />
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   INVENTORY TAB
   ═══════════════════════════════════════════════════ */

const InventoryTab = () => {
  const [tab, setTab] = useState('stock');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      let r: any;
      if (tab === 'stock') r = await api.stock();
      else if (tab === 'items') r = await api.items();
      else r = await api.warehouses();
      setData(r.data?.data || r.data || []);
    } catch { message.error('Failed to load'); }
    setLoading(false);
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      if (tab === 'items') await api.createItem(values);
      else if (tab === 'warehouses') await api.createWarehouse(values);
      message.success('Created');
      setModal(false);
      form.resetFields();
      load();
    } catch { /* validation */ }
  };

  const columns: any[] = tab === 'stock' ? [
    { title: 'Item', dataIndex: 'item_code', key: 'code',
      render: (v: string, r: any) => <div><Text strong>{v}</Text><br /><Text type="secondary">{r.name}</Text></div> },
    { title: 'Warehouse', dataIndex: 'warehouse_name', key: 'wh' },
    { title: 'On Hand', dataIndex: 'on_hand', key: 'oh', render: (v: number) => <Text strong>{fmt(v)}</Text> },
    { title: 'Reserved', dataIndex: 'reserved', key: 'res', render: (v: number) => fmt(v) },
    { title: 'Available', dataIndex: 'available', key: 'avail',
      render: (v: number) => <Text type={v <= 0 ? 'danger' : undefined} strong>{fmt(v)}</Text> },
    { title: 'Unit Cost', dataIndex: 'unit_cost', key: 'uc', render: (v: number) => fmtEgp(v) },
    { title: 'Value', dataIndex: 'value', key: 'val',
      render: (v: number) => <Text strong>{fmtEgp(v)}</Text> },
  ] : tab === 'items' ? [
    { title: 'Code', dataIndex: 'item_code', key: 'code',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Category', dataIndex: 'category', key: 'cat',
      render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
    { title: 'Unit', dataIndex: 'unit', key: 'unit' },
    { title: 'Cost', dataIndex: 'cost_price', key: 'cost', render: (v: number) => fmtEgp(v) },
    { title: 'Price', dataIndex: 'selling_price', key: 'price', render: (v: number) => fmtEgp(v) },
    { title: 'Stock', dataIndex: 'on_hand', key: 'stock', render: (v: number) => fmt(v || 0) },
    { title: 'Reorder', dataIndex: 'reorder_point', key: 'rp', render: (v: number) => fmt(v || 0) },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={v === 'active' ? 'green' : 'red'}>{v}</Tag> },
  ] : [
    { title: 'Code', dataIndex: 'code', key: 'code', render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Manager', dataIndex: 'manager', key: 'mgr' },
    { title: 'Address', dataIndex: 'address', key: 'addr' },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color="green">{v}</Tag> },
  ];

  const totalValue = tab === 'stock' ? data.reduce((s: number, r: any) => s + (r.value || 0), 0) : 0;

  return (
    <div>
      <Tabs activeKey={tab} onChange={setTab} items={[
        { key: 'stock', label: `Stock (${data.length})` },
        { key: 'items', label: 'Items' },
        { key: 'warehouses', label: 'Warehouses' },
      ]} />
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
          {tab !== 'stock' && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>
              {tab === 'items' ? 'Add Item' : 'Add Warehouse'}
            </Button>
          )}
        </Space>
        {tab === 'stock' && (
          <Text strong style={{ fontSize: 16 }}>Total Value: {fmtEgp(totalValue)}</Text>
        )}
      </div>
      <Table dataSource={data} columns={columns} rowKey="id" size="small"
        loading={loading} pagination={{ pageSize: 20 }} />

      <Modal title={tab === 'items' ? 'Add Item' : 'Add Warehouse'}
        open={modal} onOk={handleCreate} onCancel={() => setModal(false)} width={600}>
        <Form form={form} layout="vertical">
          {tab === 'items' ? (
            <>
              <Form.Item name="name" label="Item Name" rules={[{ required: true }]}>
                <Input placeholder="Samsung Galaxy S24" />
              </Form.Item>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="category" label="Category">
                    <Input placeholder="Electronics" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="unit" label="Unit" initialValue="piece">
                    <Select options={[
                      { value: 'piece', label: 'Piece' },
                      { value: 'kg', label: 'Kilogram' },
                      { value: 'box', label: 'Box' },
                      { value: 'carton', label: 'Carton' },
                      { value: 'liter', label: 'Liter' },
                    ]} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="cost_price" label="Cost Price" rules={[{ required: true }]}>
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="selling_price" label="Selling Price" rules={[{ required: true }]}>
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="reorder_point" label="Reorder Point">
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="barcode" label="Barcode">
                    <Input />
                  </Form.Item>
                </Col>
              </Row>
            </>
          ) : (
            <>
              <Form.Item name="name" label="Warehouse Name" rules={[{ required: true }]}>
                <Input placeholder="Main Warehouse" />
              </Form.Item>
              <Form.Item name="address" label="Address">
                <Input placeholder="Cairo, Egypt" />
              </Form.Item>
              <Form.Item name="manager" label="Manager">
                <Input placeholder="Ahmed" />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   CUSTOMERS TAB
   ═══════════════════════════════════════════════════ */

const CustomersTab = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r: any = await api.customers();
      setData(r.data?.data || r.data || []);
    } catch { message.error('Failed to load'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await api.createCustomer(values);
      message.success('Customer created');
      setModal(false);
      form.resetFields();
      load();
    } catch { /* validation */ }
  };

  const columns = [
    { title: 'Code', dataIndex: 'customer_code', key: 'code',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Contact', dataIndex: 'contact_person', key: 'contact' },
    { title: 'Phone', dataIndex: 'phone', key: 'phone' },
    { title: 'Territory', dataIndex: 'territory', key: 'terr',
      render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
    { title: 'Salesman', dataIndex: 'salesman', key: 'sm' },
    { title: 'Credit Limit', dataIndex: 'credit_limit', key: 'cl',
      render: (v: number) => fmtEgp(v) },
    { title: 'Balance', dataIndex: 'current_balance', key: 'bal',
      render: (v: number) => <Text type={v > 0 ? 'danger' : undefined}>{fmtEgp(v)}</Text> },
    { title: 'Terms', dataIndex: 'payment_terms', key: 'terms' },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={v === 'active' ? 'green' : 'red'}>{v}</Tag> },
  ];

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>
          Add Customer
        </Button>
      </div>
      <Table dataSource={data} columns={columns} rowKey="id" size="small"
        loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="Add Customer" open={modal} onOk={handleCreate} onCancel={() => setModal(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Customer Name" rules={[{ required: true }]}>
            <Input placeholder="Cairo Electronics Store" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="contact_person" label="Contact Person">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="Phone">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>
          <Form.Item name="address" label="Address">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="credit_limit" label="Credit Limit" initialValue={0}>
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="territory" label="Territory">
                <Input placeholder="Cairo" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="payment_terms" label="Payment Terms" initialValue="net30">
                <Select options={[
                  { value: 'cod', label: 'Cash on Delivery' },
                  { value: 'net15', label: 'Net 15' },
                  { value: 'net30', label: 'Net 30' },
                  { value: 'net60', label: 'Net 60' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   SUPPLIERS TAB
   ═══════════════════════════════════════════════════ */

const SuppliersTab = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r: any = await api.suppliers();
      setData(r.data?.data || r.data || []);
    } catch { message.error('Failed to load'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await api.createSupplier(values);
      message.success('Supplier created');
      setModal(false);
      form.resetFields();
      load();
    } catch { /* validation */ }
  };

  const columns = [
    { title: 'Code', dataIndex: 'supplier_code', key: 'code',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Contact', dataIndex: 'contact_person', key: 'contact' },
    { title: 'Phone', dataIndex: 'phone', key: 'phone' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Terms', dataIndex: 'payment_terms', key: 'terms' },
    { title: 'Lead Time', dataIndex: 'lead_time_days', key: 'lt',
      render: (v: number) => `${v} days` },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={v === 'active' ? 'green' : 'red'}>{v}</Tag> },
  ];

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>
          Add Supplier
        </Button>
      </div>
      <Table dataSource={data} columns={columns} rowKey="id" size="small"
        loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="Add Supplier" open={modal} onOk={handleCreate} onCancel={() => setModal(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Supplier Name" rules={[{ required: true }]}>
            <Input placeholder="Samsung Egypt" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="contact_person" label="Contact Person">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="Phone">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>
          <Form.Item name="address" label="Address">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="payment_terms" label="Payment Terms" initialValue="net30">
                <Select options={[
                  { value: 'cod', label: 'Cash on Delivery' },
                  { value: 'net15', label: 'Net 15' },
                  { value: 'net30', label: 'Net 30' },
                  { value: 'net60', label: 'Net 60' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="lead_time_days" label="Lead Time (days)" initialValue={7}>
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   PRICING TAB
   ═══════════════════════════════════════════════════ */

const PricingTab = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r: any = await api.priceLists();
      setData(r.data?.data || r.data || []);
    } catch { message.error('Failed to load'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const columns = [
    { title: 'List Name', dataIndex: 'list_name', key: 'name',
      render: (v: string) => <Text strong>{v}</Text> },
    { title: 'Description', dataIndex: 'description', key: 'desc' },
    { title: 'Default', dataIndex: 'is_default', key: 'def',
      render: (v: boolean) => v ? <Tag color="blue">Default</Tag> : '-' },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (v: string) => <Tag color={v === 'active' ? 'green' : 'red'}>{v}</Tag> },
  ];

  return (
    <div>
      <Table dataSource={data} columns={columns} rowKey="id" size="small"
        loading={loading} pagination={false} />
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   MAIN TRADING PAGE
   ═══════════════════════════════════════════════════ */

const TradingPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  const tabItems = [
    { key: 'dashboard', label: <span><DashboardOutlined /> Dashboard</span> },
    { key: 'sales', label: <span><ShopOutlined /> Sales</span> },
    { key: 'purchasing', label: <span><ShoppingCartOutlined /> Purchasing</span> },
    { key: 'inventory', label: <span><InboxOutlined /> Inventory</span> },
    { key: 'customers', label: <span><TeamOutlined /> Customers</span> },
    { key: 'suppliers', label: <span><CarOutlined /> Suppliers</span> },
    { key: 'pricing', label: <span><PercentageOutlined /> Pricing</span> },
  ];

  const renderTab = () => {
    switch (activeTab) {
      case 'dashboard': return <DashboardTab />;
      case 'sales': return <SalesTab />;
      case 'purchasing': return <PurchasingTab />;
      case 'inventory': return <InventoryTab />;
      case 'customers': return <CustomersTab />;
      case 'suppliers': return <SuppliersTab />;
      case 'pricing': return <PricingTab />;
      default: return <DashboardTab />;
    }
  };

  return (
    <div style={{ padding: 0 }}>
      <div style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '0 0 24px 24px', padding: '28px 32px', marginBottom: 24,
        boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{
            width: 52, height: 52, borderRadius: 16, background: 'rgba(255,255,255,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, color: '#fff',
          }}>
            <ShopOutlined />
          </div>
          <div>
            <h1 style={{ color: '#fff', margin: 0, fontSize: 22, fontWeight: 700 }}>
              Trading ERP
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.85)', margin: 0, fontSize: 13 }}>
              Sales • Purchasing • Inventory • Distribution
            </p>
          </div>
        </div>
      </div>

      <div style={{ padding: '0 24px' }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab}
          items={tabItems} size="large"
          style={{ marginBottom: 0 }} />
        {renderTab()}
      </div>
    </div>
  );
};

export default TradingPage;
