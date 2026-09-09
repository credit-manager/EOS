/**
 * Retail ERP Professional — Workspace
 * POS → Cash Management → Loyalty → Promotions → Analytics
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Typography, Space, Spin, Button, Tag, Table, Statistic,
  Tabs, Modal, Form, Input, Select, message, InputNumber, Empty,
  Divider, Badge,
} from 'antd';
import {
  ShoppingCartOutlined, TeamOutlined,
  PlusOutlined, ReloadOutlined, BarcodeOutlined, WalletOutlined,
  TrophyOutlined, PercentageOutlined, DashboardOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import apiClient from '../services/apiClient';

const { Text } = Typography;

/* ═══════════════════════════════════════════════════
   API Client
   ═══════════════════════════════════════════════════ */

const api = {
  dashboard: (): Promise<any> => apiClient.get('/retail/dashboard'),
  // Registers
  registers: (): Promise<any> => apiClient.get('/retail/registers'),
  createRegister: (d: any): Promise<any> => apiClient.post('/retail/registers', d),
  // Cashiers
  cashiers: (): Promise<any> => apiClient.get('/retail/cashiers'),
  createCashier: (d: any): Promise<any> => apiClient.post('/retail/cashiers', d),
  // Barcode
  barcode: (bc: string): Promise<any> => apiClient.get(`/retail/items/barcode/${bc}`),
  // Cash
  openSession: (d: any): Promise<any> => apiClient.post('/retail/cash/sessions/open', d),
  closeSession: (id: string, amt: number): Promise<any> => apiClient.post(`/retail/cash/sessions/${id}/close?closing_amount=${amt}`),
  cashSessions: (): Promise<any> => apiClient.get('/retail/cash/sessions'),
  cashMovement: (d: any): Promise<any> => apiClient.post('/retail/cash/movements', d),
  // POS
  createSale: (d: any): Promise<any> => apiClient.post('/retail/pos/sales', d),
  createReturn: (d: any): Promise<any> => apiClient.post('/retail/pos/returns', d),
  voidSale: (id: string): Promise<any> => apiClient.post(`/retail/pos/sales/${id}/void`),
  suspended: (): Promise<any> => apiClient.get('/retail/pos/suspended'),
  suspendSale: (d: any): Promise<any> => apiClient.post('/retail/pos/suspended', d),
  recallSale: (id: string): Promise<any> => apiClient.post(`/retail/pos/suspended/${id}/recall`),
  // Loyalty
  loyaltyTiers: (): Promise<any> => apiClient.get('/retail/loyalty/tiers'),
  loyaltyAccounts: (): Promise<any> => apiClient.get('/retail/loyalty/accounts'),
  createLoyaltyAccount: (d: any): Promise<any> => apiClient.post('/retail/loyalty/accounts', d),
  loyaltyTransactions: (id: string): Promise<any> => apiClient.get(`/retail/loyalty/transactions/${id}`),
  // Promotions
  promotions: (): Promise<any> => apiClient.get('/retail/promotions'),
  createPromotion: (d: any): Promise<any> => apiClient.post('/retail/promotions', d),
  // Analytics
  topProducts: (): Promise<any> => apiClient.get('/retail/analytics/top-products'),
  cashierPerf: (): Promise<any> => apiClient.get('/retail/analytics/cashier-performance'),
  basketSize: (): Promise<any> => apiClient.get('/retail/analytics/basket-size'),
};

/* ═══════════════════════════════════════════════════
   POS Cart Item
   ═══════════════════════════════════════════════════ */

interface CartItem {
  item_id: string;
  name: string;
  barcode: string;
  qty: number;
  unit_price: number;
  discount_pct: number;
  line_total: number;
}

/* ═══════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════ */

const RetailPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [dashData, setDashData] = useState<any>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.dashboard();
      setDashData(r.data?.data || r.data);
    } catch { message.error('Failed to load dashboard'); }
    setLoading(false);
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  return (
    <div style={{ padding: 0 }}>
      <Tabs
        defaultActiveKey="pos"
        items={[
          { key: 'dashboard', label: <span><DashboardOutlined /> Dashboard</span>, children: <DashboardTab data={dashData} loading={loading} /> },
          { key: 'pos', label: <span><ShoppingCartOutlined /> POS</span>, children: <POSTab /> },
          { key: 'cash', label: <span><WalletOutlined /> Cash</span>, children: <CashTab /> },
          { key: 'loyalty', label: <span><TrophyOutlined /> Loyalty</span>, children: <LoyaltyTab /> },
          { key: 'promotions', label: <span><PercentageOutlined /> Promotions</span>, children: <PromotionsTab /> },
          { key: 'analytics', label: <span><DashboardOutlined /> Analytics</span>, children: <AnalyticsTab /> },
        ]}
      />
    </div>
  );
};

export default RetailPage;

/* ═══════════════════════════════════════════════════
   DASHBOARD TAB
   ═══════════════════════════════════════════════════ */

const DashboardTab: React.FC<{ data: any; loading: boolean }> = ({ data, loading }) => {
  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!data) return <Empty description="No data" />;

  const today = data.today || {};
  const month = data.month || {};
  const returns = data.returns_month || {};

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}><Card><Statistic title="Today Sales" value={today.transactions || 0} prefix={<ShoppingCartOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="Today Revenue" value={today.revenue || 0} precision={2} prefix="EGP" /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="Month Revenue" value={month.revenue || 0} precision={2} prefix="EGP" valueStyle={{ color: '#3f8600' }} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="Month Returns" value={returns.amount || 0} precision={2} prefix="EGP" valueStyle={{ color: '#cf1322' }} /></Card></Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={12} sm={6}><Card><Statistic title="Cashiers" value={data.active_cashiers || 0} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="Open Sessions" value={data.open_sessions || 0} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="Loyalty Members" value={data.loyalty_members || 0} prefix={<TeamOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="Active Promos" value={data.active_promotions || 0} prefix={<PercentageOutlined />} /></Card></Col>
      </Row>
      {data.top_items && data.top_items.length > 0 && (
        <Card title="Top Products This Month" style={{ marginTop: 16 }}>
          <Table dataSource={data.top_items} rowKey="name" size="small" pagination={false}
            columns={[
              { title: 'Product', dataIndex: 'name', key: 'name' },
              { title: 'Qty Sold', dataIndex: 'qty', key: 'qty', render: (v: number) => v?.toFixed(0) },
              { title: 'Revenue', dataIndex: 'revenue', key: 'revenue', render: (v: number) => `${v?.toFixed(2)} EGP` },
            ]}
          />
        </Card>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   POS TAB — Main Point of Sale Interface
   ═══════════════════════════════════════════════════ */

const POSTab: React.FC = () => {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [barcode, setBarcode] = useState('');
  const [registers, setRegisters] = useState<any[]>([]);
  const [cashiers, setCashiers] = useState<any[]>([]);
  const [selectedReg, setSelectedReg] = useState<string>('');
  const [selectedCashier, setSelectedCashier] = useState<string>('');
  const [customerId, setCustomerId] = useState<string>('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paidAmount, setPaidAmount] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [suspended, setSuspended] = useState<any[]>([]);
  const [showReturn, setShowReturn] = useState(false);
  const [showSuspend, setShowSuspend] = useState(false);

  const loadRegisters = useCallback(async () => {
    try {
      const r = await api.registers();
      setRegisters(r.data?.data || []);
      const c = await api.cashiers();
      setCashiers(c.data?.data || []);
      const s = await api.suspended();
      setSuspended(s.data?.data || []);
    } catch {}
  }, []);

  useEffect(() => { loadRegisters(); }, [loadRegisters]);

  const subtotal = cart.reduce((s, i) => s + i.line_total, 0);
  const tax = subtotal * 0.14;
  const total = subtotal + tax;

  const scanBarcode = async () => {
    if (!barcode.trim()) return;
    try {
      const r = await api.barcode(barcode.trim());
      const item = r.data?.data;
      if (!item) { message.warning('Item not found'); return; }
      setCart(prev => {
        const existing = prev.find(i => i.item_id === item.id);
        if (existing) {
          return prev.map(i => i.item_id === item.id
            ? { ...i, qty: i.qty + 1, line_total: (i.qty + 1) * i.unit_price * (1 - i.discount_pct / 100) }
            : i);
        }
        const newLine: CartItem = {
          item_id: item.id, name: item.name, barcode: barcode,
          qty: 1, unit_price: item.selling_price, discount_pct: 0,
          line_total: item.selling_price,
        };
        return [...prev, newLine];
      });
      setBarcode('');
    } catch { message.error('Failed to lookup barcode'); }
  };

  const updateQty = (id: string, qty: number) => {
    if (qty < 1) return;
    setCart(prev => prev.map(i => i.item_id === id
      ? { ...i, qty, line_total: qty * i.unit_price * (1 - i.discount_pct / 100) }
      : i));
  };

  const removeItem = (id: string) => {
    setCart(prev => prev.filter(i => i.item_id !== id));
  };

  const completeSale = async () => {
    if (cart.length === 0) { message.warning('Cart is empty'); return; }
    if (!selectedReg) { message.warning('Select a register'); return; }
    if (!selectedCashier) { message.warning('Select a cashier'); return; }
    if (paidAmount < total) { message.warning(`Paid ${paidAmount} < total ${total.toFixed(2)}`); return; }

    setLoading(true);
    try {
      const r = await api.createSale({
        register_id: selectedReg,
        cashier_id: selectedCashier,
        customer_id: customerId || undefined,
        payment_method: paymentMethod,
        paid_amount: paidAmount,
        lines: cart.map(i => ({
          item_id: i.item_id, qty: i.qty, unit_price: i.unit_price, discount_pct: i.discount_pct,
        })),
      });
      const sale = r.data?.data;
      message.success(`Sale ${sale.sale_number} — ${sale.total.toFixed(2)} EGP — Change: ${sale.change.toFixed(2)}`);
      setCart([]);
      setPaidAmount(0);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Sale failed');
    }
    setLoading(false);
  };

  const suspendSale = async () => {
    if (cart.length === 0 || !selectedReg || !selectedCashier) { message.warning('Cart empty or no register/cashier'); return; }
    setLoading(true);
    try {
      await api.suspendSale({
        register_id: selectedReg, cashier_id: selectedCashier,
        items_json: JSON.stringify(cart), subtotal, tax_amount: tax, total,
      });
      message.success('Sale suspended');
      setCart([]);
      setShowSuspend(false);
      loadRegisters();
    } catch { message.error('Failed to suspend'); }
    setLoading(false);
  };

  const recallSale = async (id: string) => {
    try {
      const r = await api.recallSale(id);
      const data = r.data?.data;
      if (data?.items_json) {
        setCart(JSON.parse(data.items_json));
        message.success('Sale recalled');
      }
      loadRegisters();
    } catch { message.error('Failed to recall'); }
  };

  return (
    <div>
      <Row gutter={16}>
        {/* Left: Cart */}
        <Col xs={24} lg={16}>
          <Card title="POS — Scan & Sell" style={{ height: '100%' }}>
            <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
              <Space.Compact style={{ width: '100%' }}>
                <Input
                  prefix={<BarcodeOutlined />}
                  placeholder="Scan barcode or enter item code..."
                  value={barcode}
                  onChange={e => setBarcode(e.target.value)}
                  onPressEnter={scanBarcode}
                  size="large"
                />
                <Button type="primary" onClick={scanBarcode} size="large">Add</Button>
              </Space.Compact>
            </Space>

            {cart.length === 0 ? (
              <Empty description="Scan a barcode to start" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Table dataSource={cart} rowKey="item_id" size="small" pagination={false}
                columns={[
                  { title: 'Item', dataIndex: 'name', key: 'name' },
                  { title: 'Price', dataIndex: 'unit_price', key: 'price', render: (v: number) => `${v.toFixed(2)}` },
                  { title: 'Qty', dataIndex: 'qty', key: 'qty',
                    render: (v: number, r: any) => (
                      <Space>
                        <Button size="small" onClick={() => updateQty(r.item_id, v - 1)}>-</Button>
                        <Text strong>{v}</Text>
                        <Button size="small" onClick={() => updateQty(r.item_id, v + 1)}>+</Button>
                      </Space>
                    ) },
                  { title: 'Total', dataIndex: 'line_total', key: 'total', render: (v: number) => `${v.toFixed(2)}` },
                  { title: '', key: 'remove', render: (_: any, r: any) => (
                    <Button type="text" danger size="small" icon={<CloseCircleOutlined />} onClick={() => removeItem(r.item_id)} />
                  ) },
                ]}
              />
            )}
          </Card>
        </Col>

        {/* Right: Payment & Controls */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card size="small" title="Register & Cashier">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Select placeholder="Select register" style={{ width: '100%' }} value={selectedReg || undefined}
                  onChange={setSelectedReg}>
                  {registers.map((r: any) => <Select.Option key={r.id} value={r.id}>{r.name} ({r.code})</Select.Option>)}
                </Select>
                <Select placeholder="Select cashier" style={{ width: '100%' }} value={selectedCashier || undefined}
                  onChange={setSelectedCashier}>
                  {cashiers.map((c: any) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
                </Select>
                <Input placeholder="Customer ID (optional)" value={customerId} onChange={e => setCustomerId(e.target.value)} size="small" />
              </Space>
            </Card>

            <Card size="small" title="Payment">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Select value={paymentMethod} onChange={setPaymentMethod} style={{ width: '100%' }}>
                  <Select.Option value="cash">Cash</Select.Option>
                  <Select.Option value="card">Card</Select.Option>
                  <Select.Option value="mobile">Mobile Pay</Select.Option>
                </Select>
                <InputNumber style={{ width: '100%' }} size="large" placeholder="Paid amount"
                  value={paidAmount} onChange={v => setPaidAmount(v || 0)} min={0} prefix="EGP" />
              </Space>
            </Card>

            <Card size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Row justify="space-between"><Text>Subtotal</Text><Text>{subtotal.toFixed(2)} EGP</Text></Row>
                <Row justify="space-between"><Text>Tax (14%)</Text><Text>{tax.toFixed(2)} EGP</Text></Row>
                <Divider style={{ margin: '4px 0' }} />
                <Row justify="space-between"><Text strong style={{ fontSize: 18 }}>Total</Text><Text strong style={{ fontSize: 18 }}>{total.toFixed(2)} EGP</Text></Row>
                {paidAmount > total && (
                  <Row justify="space-between"><Text type="success">Change</Text><Text type="success" strong>{(paidAmount - total).toFixed(2)} EGP</Text></Row>
                )}
              </Space>
            </Card>

            <Space style={{ width: '100%' }}>
              <Button type="primary" block size="large" loading={loading} onClick={completeSale} style={{ flex: 2 }}>
                Complete Sale
              </Button>
              <Button block size="large" onClick={() => setShowSuspend(true)} style={{ flex: 1 }}>
                Suspend
              </Button>
            </Space>
            <Button block onClick={() => setShowReturn(true)}>Return</Button>
          </Space>
        </Col>
      </Row>

      {/* Suspended Sales */}
      {suspended.length > 0 && (
        <Card title="Suspended Sales" style={{ marginTop: 16 }} size="small">
          <Table dataSource={suspended} rowKey="id" size="small" pagination={false}
            columns={[
              { title: 'ID', dataIndex: 'id', key: 'id', render: (v: string) => v?.slice(0, 8) },
              { title: 'Total', dataIndex: 'total', key: 'total', render: (v: number) => `${v?.toFixed(2)} EGP` },
              { title: 'Suspended At', dataIndex: 'suspended_at', key: 'time' },
              { title: '', key: 'recall', render: (_: any, r: any) => (
                <Button type="link" onClick={() => recallSale(r.id)}>Recall</Button>
              ) },
            ]}
          />
        </Card>
      )}

      {/* Return Modal */}
      <Modal title="Process Return" open={showReturn} onCancel={() => setShowReturn(false)} footer={null}>
        <ReturnForm registers={registers} cashiers={cashiers} onComplete={() => { setShowReturn(false); loadRegisters(); }} />
      </Modal>

      {/* Suspend Modal */}
      <Modal title="Suspend Sale" open={showSuspend} onOk={suspendSale} onCancel={() => setShowSuspend(false)} okText="Suspend">
        <Text>This will suspend the current cart ({cart.length} items, {total.toFixed(2)} EGP).</Text>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   RETURN FORM
   ═══════════════════════════════════════════════════ */

const ReturnForm: React.FC<{ registers: any[]; cashiers: any[]; onComplete: () => void }> = ({ registers, cashiers, onComplete }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await api.createReturn({
        original_sale_id: values.sale_id,
        register_id: values.register_id,
        cashier_id: values.cashier_id,
        lines: [{ item_id: values.item_id, qty: values.qty, unit_price: values.unit_price }],
        reason: values.reason,
      });
      message.success('Return processed');
      onComplete();
    } catch (e: any) {
      if (e?.response?.data?.detail) message.error(e.response.data.detail);
    }
    setLoading(false);
  };

  return (
    <Form form={form} layout="vertical">
      <Form.Item name="sale_id" label="Original Sale ID" rules={[{ required: true }]}><Input /></Form.Item>
      <Form.Item name="register_id" label="Register" rules={[{ required: true }]}>
        <Select>{registers.map((r: any) => <Select.Option key={r.id} value={r.id}>{r.name}</Select.Option>)}</Select>
      </Form.Item>
      <Form.Item name="cashier_id" label="Cashier" rules={[{ required: true }]}>
        <Select>{cashiers.map((c: any) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}</Select>
      </Form.Item>
      <Form.Item name="item_id" label="Item ID" rules={[{ required: true }]}><Input /></Form.Item>
      <Row gutter={8}>
        <Col span={12}><Form.Item name="qty" label="Qty" rules={[{ required: true }]}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
        <Col span={12}><Form.Item name="unit_price" label="Unit Price" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
      </Row>
      <Form.Item name="reason" label="Reason"><Input.TextArea rows={2} /></Form.Item>
      <Button type="primary" block loading={loading} onClick={submit}>Process Return</Button>
    </Form>
  );
};

/* ═══════════════════════════════════════════════════
   CASH MANAGEMENT TAB
   ═══════════════════════════════════════════════════ */

const CashTab: React.FC = () => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [registers, setRegisters] = useState<any[]>([]);
  const [cashiers, setCashiers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOpen, setShowOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const sRes: any = await api.cashSessions();
      const rRes: any = await api.registers();
      const cRes: any = await api.cashiers();
      setSessions(sRes.data?.data || []);
      setRegisters(rRes.data?.data || []);
      setCashiers(cRes.data?.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const openSession = async (values: any) => {
    try {
      await api.openSession(values);
      message.success('Session opened');
      setShowOpen(false);
      load();
    } catch (e: any) { message.error(e?.response?.data?.detail || 'Failed'); }
  };

  const closeSession = async (id: string) => {
    Modal.confirm({
      title: 'Close Session',
      content: 'Enter closing amount:',
      okText: 'Close',
      onOk: async () => {
        try {
          const r = await api.closeSession(id, 0);
          message.success(`Closed. Variance: ${r.data?.data?.variance}`);
          load();
        } catch (e: any) { message.error(e?.response?.data?.detail || 'Failed'); }
      },
    });
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowOpen(true)}>Open Session</Button>
        <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
      </Space>
      {loading ? <Spin /> : (
        <Table dataSource={sessions} rowKey="id" size="small"
          columns={[
            { title: 'Session', dataIndex: 'session_number', key: 'sn' },
            { title: 'Register', dataIndex: 'register_id', key: 'reg', render: (v: string) => v?.slice(0, 8) },
            { title: 'Opening', dataIndex: 'opening', key: 'opening', render: (v: number) => `${v?.toFixed(2)} EGP` },
            { title: 'Closing', dataIndex: 'closing', key: 'closing', render: (v: number) => v != null ? `${v.toFixed(2)} EGP` : '-' },
            { title: 'Expected', dataIndex: 'expected', key: 'expected', render: (v: number) => v != null ? `${v.toFixed(2)} EGP` : '-' },
            { title: 'Variance', dataIndex: 'variance', key: 'variance', render: (v: number) => v != null ? (
              <Text type={v === 0 ? 'success' : 'danger'}>{v.toFixed(2)} EGP</Text>
            ) : '-' },
            { title: 'Status', dataIndex: 'status', key: 'status', render: (v: string) => (
              <Badge status={v === 'open' ? 'processing' : 'default'} text={v} />
            )},
            { title: '', key: 'close', render: (_: any, r: any) => r.status === 'open' ? (
              <Button type="link" onClick={() => closeSession(r.id)}>Close</Button>
            ) : null },
          ]}
        />
      )}

      <Modal title="Open Cash Session" open={showOpen} onCancel={() => setShowOpen(false)} footer={null}>
        <Form layout="vertical" onFinish={openSession}>
          <Form.Item name="register_id" label="Register" rules={[{ required: true }]}>
            <Select>{registers.map((r: any) => <Select.Option key={r.id} value={r.id}>{r.name}</Select.Option>)}</Select>
          </Form.Item>
          <Form.Item name="cashier_id" label="Cashier" rules={[{ required: true }]}>
            <Select>{cashiers.map((c: any) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}</Select>
          </Form.Item>
          <Form.Item name="opening_amount" label="Opening Amount" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} prefix="EGP" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>Open Session</Button>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   LOYALTY TAB
   ═══════════════════════════════════════════════════ */

const LoyaltyTab: React.FC = () => {
  const [tiers, setTiers] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const tRes: any = await api.loyaltyTiers();
      const aRes: any = await api.loyaltyAccounts();
      setTiers(tRes.data?.data || []);
      setAccounts(aRes.data?.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <Row gutter={16}>
        <Col xs={24} md={8}>
          <Card title="Loyalty Tiers" size="small">
            {tiers.map((t: any) => (
              <Card key={t.id} size="small" style={{ marginBottom: 8 }}>
                <Row justify="space-between">
                  <Text strong>{t.name}</Text>
                  <Tag color="blue">{t.discount_pct}% off</Tag>
                </Row>
                <Text type="secondary">Min: {t.min_points} pts | Multiplier: {t.points_multiplier}x</Text>
              </Card>
            ))}
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card title="Loyalty Accounts" size="small" extra={<Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>}>
            {loading ? <Spin /> : (
              <Table dataSource={accounts} rowKey="id" size="small"
                columns={[
                  { title: 'Customer', dataIndex: 'customer_name', key: 'name' },
                  { title: 'Tier', dataIndex: 'tier', key: 'tier', render: (v: string) => <Tag color="gold">{v}</Tag> },
                  { title: 'Available', dataIndex: 'available', key: 'avail', render: (v: number) => `${v} pts` },
                  { title: 'Total Earned', dataIndex: 'total_points', key: 'total' },
                  { title: 'Redeemed', dataIndex: 'redeemed', key: 'redeemed' },
                  { title: 'Lifetime Spend', dataIndex: 'lifetime_spend', key: 'spend', render: (v: number) => `${v?.toFixed(2)} EGP` },
                ]}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   PROMOTIONS TAB
   ═══════════════════════════════════════════════════ */

const PromotionsTab: React.FC = () => {
  const [promos, setPromos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rRes: any = await api.promotions();
      setPromos(rRes.data?.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const createPromo = async (values: any) => {
    try {
      await api.createPromotion(values);
      message.success('Promotion created');
      setShowCreate(false);
      load();
    } catch (e: any) { message.error(e?.response?.data?.detail || 'Failed'); }
  };

  return (
    <div>
      <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowCreate(true)} style={{ marginBottom: 16 }}>
        Create Promotion
      </Button>
      {loading ? <Spin /> : (
        <Table dataSource={promos} rowKey="id" size="small"
          columns={[
            { title: 'Name', dataIndex: 'name', key: 'name' },
            { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
            { title: 'Discount', dataIndex: 'discount', key: 'discount', render: (v: number) => `${v}` },
            { title: 'Start', dataIndex: 'start', key: 'start' },
            { title: 'End', dataIndex: 'end', key: 'end' },
            { title: 'Status', dataIndex: 'status', key: 'status', render: (v: string) => (
              <Badge status={v === 'active' ? 'success' : 'default'} text={v} />
            ) },
          ]}
        />
      )}

      <Modal title="Create Promotion" open={showCreate} onCancel={() => setShowCreate(false)} footer={null}>
        <Form layout="vertical" onFinish={createPromo}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name_ar" label="Arabic Name"><Input /></Form.Item>
          <Form.Item name="promo_type" label="Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="percentage">Percentage</Select.Option>
              <Select.Option value="fixed">Fixed Amount</Select.Option>
              <Select.Option value="bogo">Buy One Get One</Select.Option>
              <Select.Option value="bundle">Bundle</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="discount_value" label="Discount Value" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Row gutter={8}>
            <Col span={12}><Form.Item name="start_date" label="Start Date" rules={[{ required: true }]}><Input type="date" /></Form.Item></Col>
            <Col span={12}><Form.Item name="end_date" label="End Date" rules={[{ required: true }]}><Input type="date" /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" block>Create</Button>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   ANALYTICS TAB
   ═══════════════════════════════════════════════════ */

const AnalyticsTab: React.FC = () => {
  const [topProducts, setTopProducts] = useState<any[]>([]);
  const [cashierPerf, setCashierPerf] = useState<any[]>([]);
  const [basket, setBasket] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const tRes: any = await api.topProducts();
      const cRes: any = await api.cashierPerf();
      const bRes: any = await api.basketSize();
      setTopProducts(tRes.data?.data || []);
      setCashierPerf(cRes.data?.data || []);
      setBasket(bRes.data?.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={8}>
        <Card title="Top Products" size="small">
          <Table dataSource={topProducts} rowKey="name" size="small" pagination={{ pageSize: 10 }}
            columns={[
              { title: 'Product', dataIndex: 'name', key: 'name' },
              { title: 'Qty', dataIndex: 'qty_sold', key: 'qty', render: (v: number) => v?.toFixed(0) },
              { title: 'Revenue', dataIndex: 'revenue', key: 'rev', render: (v: number) => `${v?.toFixed(0)} EGP` },
            ]}
          />
        </Card>
      </Col>
      <Col xs={24} lg={8}>
        <Card title="Cashier Performance" size="small">
          <Table dataSource={cashierPerf} rowKey="cashier" size="small" pagination={false}
            columns={[
              { title: 'Cashier', dataIndex: 'cashier', key: 'name' },
              { title: 'Sales', dataIndex: 'transactions', key: 'txns' },
              { title: 'Total', dataIndex: 'total_sales', key: 'total', render: (v: number) => `${v?.toFixed(0)} EGP` },
              { title: 'Avg', dataIndex: 'avg_sale', key: 'avg', render: (v: number) => `${v?.toFixed(0)} EGP` },
            ]}
          />
        </Card>
      </Col>
      <Col xs={24} lg={8}>
        <Card title="Basket Size Trend" size="small">
          <Table dataSource={basket.slice(-10)} rowKey="date" size="small" pagination={false}
            columns={[
              { title: 'Date', dataIndex: 'date', key: 'date', render: (v: string) => v?.slice(5, 10) },
              { title: 'Txns', dataIndex: 'transactions', key: 'txns' },
              { title: 'Avg Items', dataIndex: 'avg_items', key: 'items', render: (v: number) => v?.toFixed(1) },
              { title: 'Avg Basket', dataIndex: 'avg_basket', key: 'basket', render: (v: number) => `${v?.toFixed(0)} EGP` },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
};
