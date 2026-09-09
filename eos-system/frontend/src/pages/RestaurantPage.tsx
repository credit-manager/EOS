/**
 * Restaurant ERP Professional — Workspace
 * Built on Commerce Engine + Core Platform
 * Tabs: Dashboard → Floor → POS → Kitchen → Menu → Inventory → Analytics
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Typography, Space, Spin, Button, Tag, Table, Statistic,
  Tabs, Modal, Form, Input, Select, message, InputNumber, Empty,
  Divider, Progress,
} from 'antd';
import {
  DashboardOutlined, AppstoreOutlined, ShoppingCartOutlined,
  MenuOutlined, ShopOutlined, BarChartOutlined,
  PlusOutlined, FireOutlined, ClockCircleOutlined,
  UserOutlined, DollarOutlined, WarningOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import apiClient from '../services/apiClient';

const { Text, Title } = Typography;

/* ═══════════════════════════════════════════════════
   API Client
   ═══════════════════════════════════════════════════ */

const api = {
  dashboard: (): Promise<any> => apiClient.get('/restaurant/dashboard'),
  // Sections & Tables
  sections: (): Promise<any> => apiClient.get('/restaurant/sections'),
  createSection: (d: any): Promise<any> => apiClient.post('/restaurant/sections', d),
  tables: (): Promise<any> => apiClient.get('/restaurant/tables'),
  createTable: (d: any): Promise<any> => apiClient.post('/restaurant/tables', d),
  updateTableStatus: (id: string, s: string): Promise<any> => apiClient.post(`/restaurant/tables/${id}/status?status=${s}`),
  // Reservations
  reservations: (): Promise<any> => apiClient.get('/restaurant/reservations'),
  createReservation: (d: any): Promise<any> => apiClient.post('/restaurant/reservations', d),
  checkinReservation: (id: string): Promise<any> => apiClient.post(`/restaurant/reservations/${id}/checkin`),
  // Menu
  menuCategories: (): Promise<any> => apiClient.get('/restaurant/menu/categories'),
  createMenuCategory: (d: any): Promise<any> => apiClient.post('/restaurant/menu/categories', d),
  menuItems: (cat?: string): Promise<any> => apiClient.get('/restaurant/menu/items', { params: cat ? { category_id: cat } : {} }),
  createMenuItem: (d: any): Promise<any> => apiClient.post('/restaurant/menu/items', d),
  updateMenuItem: (id: string, d: any): Promise<any> => apiClient.put(`/restaurant/menu/items/${id}`, d),
  toggleAvailability: (id: string): Promise<any> => apiClient.post(`/restaurant/menu/items/${id}/availability`),
  // Modifiers
  modifierGroups: (): Promise<any> => apiClient.get('/restaurant/menu/modifier-groups'),
  createModifierGroup: (d: any): Promise<any> => apiClient.post('/restaurant/menu/modifier-groups', d),
  createModifier: (d: any): Promise<any> => apiClient.post('/restaurant/menu/modifiers', d),
  // Combos
  combos: (): Promise<any> => apiClient.get('/restaurant/menu/combos'),
  createCombo: (d: any): Promise<any> => apiClient.post('/restaurant/menu/combos', d),
  // Recipes
  recipes: (): Promise<any> => apiClient.get('/restaurant/recipes'),
  createRecipe: (d: any): Promise<any> => apiClient.post('/restaurant/recipes', d),
  getRecipe: (id: string): Promise<any> => apiClient.get(`/restaurant/recipes/${id}`),
  // Orders
  orders: (s?: string): Promise<any> => apiClient.get('/restaurant/orders', { params: s ? { status: s } : {} }),
  getOrder: (id: string): Promise<any> => apiClient.get(`/restaurant/orders/${id}`),
  createOrder: (d: any): Promise<any> => apiClient.post('/restaurant/orders', d),
  sendToKitchen: (id: string): Promise<any> => apiClient.post(`/restaurant/orders/${id}/send-to-kitchen`),
  payOrder: (id: string, d: any): Promise<any> => apiClient.post(`/restaurant/orders/${id}/pay`, d),
  voidOrder: (id: string): Promise<any> => apiClient.post(`/restaurant/orders/${id}/void`),
  // Kitchen
  kitchenOrders: (): Promise<any> => apiClient.get('/restaurant/kitchen/orders'),
  kitchenStations: (): Promise<any> => apiClient.get('/restaurant/kitchen/stations'),
  startKitchenOrder: (id: string): Promise<any> => apiClient.post(`/restaurant/kitchen/orders/${id}/start`),
  completeKitchenOrder: (id: string): Promise<any> => apiClient.post(`/restaurant/kitchen/orders/${id}/complete`),
  // Waste
  waste: (): Promise<any> => apiClient.get('/restaurant/waste'),
  createWaste: (d: any): Promise<any> => apiClient.post('/restaurant/waste', d),
  // Cash Drawer
  cashDrawer: (): Promise<any> => apiClient.get('/restaurant/cash-drawer'),
  openCashDrawer: (d: any): Promise<any> => apiClient.post('/restaurant/cash-drawer/open', d),
  closeCashDrawer: (d: any): Promise<any> => apiClient.post('/restaurant/cash-drawer/close', d),
  // Waiters
  waiters: (): Promise<any> => apiClient.get('/restaurant/waiters'),
  createWaiter: (d: any): Promise<any> => apiClient.post('/restaurant/waiters', d),
  // Analytics
  popularItems: (): Promise<any> => apiClient.get('/restaurant/analytics/popular-items'),
  revenueByType: (): Promise<any> => apiClient.get('/restaurant/analytics/revenue-by-type'),
  foodCost: (): Promise<any> => apiClient.get('/restaurant/analytics/food-cost'),
  tableTurnover: (): Promise<any> => apiClient.get('/restaurant/analytics/table-turnover'),
};

/* ═══════════════════════════════════════════════════
   INTERFACES
   ═══════════════════════════════════════════════════ */

interface OrderLine {
  menu_item_id: string;
  name: string;
  qty: number;
  unit_price: number;
  discount_pct: number;
  line_total: number;
  modifier_ids: string[];
  notes?: string;
}

/* ═══════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════ */

const RestaurantPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  /* ── Dashboard State ── */
  const [dashData, setDashData] = useState<any>(null);

  /* ── Floor State ── */
  const [tables, setTables] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);
  const [showTableModal, setShowTableModal] = useState(false);
  const [tableForm] = Form.useForm();

  /* ── POS State ── */
  const [menuItems, setMenuItems] = useState<any[]>([]);
  const [menuCategories, setMenuCategories] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [cart, setCart] = useState<OrderLine[]>([]);
  const [activeOrders, setActiveOrders] = useState<any[]>([]);
  const [orderType, setOrderType] = useState('dine_in');
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [guestsCount] = useState(2);
  const [orderNotes, setOrderNotes] = useState('');

  /* ── Kitchen State ── */
  const [kitchenOrders, setKitchenOrders] = useState<any[]>([]);
  const [kitchenStations, setKitchenStations] = useState<any[]>([]);

  /* ── Menu Management State ── */
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showItemModal, setShowItemModal] = useState(false);
  const [catForm] = Form.useForm();
  const [itemForm] = Form.useForm();

  /* ── Recipe State ── */
  const [recipes, setRecipes] = useState<any[]>([]);
  const [showRecipeModal, setShowRecipeModal] = useState(false);
  const [recipeForm] = Form.useForm();

  /* ── Inventory State ── */
  const [wasteList, setWasteList] = useState<any[]>([]);
  const [showWasteModal, setShowWasteModal] = useState(false);
  const [wasteForm] = Form.useForm();

  /* ── Cash State ── */
  const [cashDrawer, setCashDrawer] = useState<any[]>([]);

  /* ── Analytics State ── */
  const [popularItems, setPopularItems] = useState<any[]>([]);
  const [revenueByType, setRevenueByType] = useState<any[]>([]);
  const [foodCostData, setFoodCostData] = useState<any[]>([]);

  /* ═══════════════════════════════════════════════════
     DATA LOADING
     ═══════════════════════════════════════════════════ */

  const loadDashboard = useCallback(async () => {
    try {
      const res = await api.dashboard();
      setDashData(res.data);
    } catch { message.error('Failed to load dashboard'); }
  }, []);

  const loadFloor = useCallback(async () => {
    try {
      const [t, s] = await Promise.all([api.tables(), api.sections()]);
      setTables(t.data || []);
      setSections(s.data || []);
    } catch { message.error('Failed to load floor data'); }
  }, []);

  const loadPOS = useCallback(async () => {
    try {
      const [mi, mc, ao] = await Promise.all([
        api.menuItems(selectedCategory || undefined),
        api.menuCategories(),
        api.orders(),
      ]);
      setMenuItems(mi.data || []);
      setMenuCategories(mc.data || []);
      setActiveOrders((ao.data || []).filter((o: any) => ['open', 'preparing', 'ready'].includes(o.status)));
    } catch { message.error('Failed to load POS data'); }
  }, [selectedCategory]);

  const loadKitchen = useCallback(async () => {
    try {
      const [ko, ks] = await Promise.all([api.kitchenOrders(), api.kitchenStations()]);
      setKitchenOrders(ko.data || []);
      setKitchenStations(ks.data || []);
    } catch { message.error('Failed to load kitchen data'); }
  }, []);

  const loadMenuMgmt = useCallback(async () => {
    try {
      const [mi, mc, r] = await Promise.all([api.menuItems(), api.menuCategories(), api.recipes()]);
      setMenuItems(mi.data || []);
      setMenuCategories(mc.data || []);
      setRecipes(r.data || []);
    } catch { message.error('Failed to load menu data'); }
  }, []);

  const loadInventory = useCallback(async () => {
    try {
      const w = await api.waste();
      setWasteList(w.data || []);
    } catch { message.error('Failed to load inventory data'); }
  }, []);

  const loadCash = useCallback(async () => {
    try {
      const cd = await api.cashDrawer();
      setCashDrawer(cd.data || []);
    } catch { message.error('Failed to load cash data'); }
  }, []);

  const loadAnalytics = useCallback(async () => {
    try {
      const [p, r, f] = await Promise.all([api.popularItems(), api.revenueByType(), api.foodCost()]);
      setPopularItems(p.data || []);
      setRevenueByType(r.data || []);
      setFoodCostData(f.data || []);
    } catch { message.error('Failed to load analytics'); }
  }, []);

  useEffect(() => {
    switch (activeTab) {
      case 'dashboard': loadDashboard(); break;
      case 'floor': loadFloor(); break;
      case 'pos': loadPOS(); break;
      case 'kitchen': loadKitchen(); break;
      case 'menu': loadMenuMgmt(); break;
      case 'inventory': loadInventory(); break;
      case 'cash': loadCash(); break;
      case 'analytics': loadAnalytics(); break;
    }
  }, [activeTab, loadDashboard, loadFloor, loadPOS, loadKitchen, loadMenuMgmt, loadInventory, loadCash, loadAnalytics]);

  /* ═══════════════════════════════════════════════════
     POS CART OPERATIONS
     ═══════════════════════════════════════════════════ */

  const addToCart = (item: any) => {
    const existing = cart.find(c => c.menu_item_id === item.id);
    if (existing) {
      setCart(cart.map(c => c.menu_item_id === item.id
        ? { ...c, qty: c.qty + 1, line_total: (c.qty + 1) * c.unit_price }
        : c));
    } else {
      setCart([...cart, {
        menu_item_id: item.id, name: item.name, qty: 1,
        unit_price: item.price, discount_pct: 0,
        line_total: item.price, modifier_ids: [],
      }]);
    }
  };

  const updateCartQty = (idx: number, qty: number) => {
    if (qty <= 0) { setCart(cart.filter((_, i) => i !== idx)); return; }
    setCart(cart.map((c, i) => i === idx
      ? { ...c, qty, line_total: qty * c.unit_price * (1 - c.discount_pct / 100) }
      : c));
  };

  const cartTotal = cart.reduce((s, c) => s + c.line_total, 0);
  const cartTax = cartTotal * 0.15;

  const submitOrder = async () => {
    if (cart.length === 0) { message.warning('Cart is empty'); return; }
    try {
      const res = await api.createOrder({
        order_type: orderType,
        table_id: selectedTable || undefined,
        guests_count: guestsCount,
        notes: orderNotes || undefined,
        lines: cart.map(c => ({
          menu_item_id: c.menu_item_id, qty: c.qty,
          unit_price: c.unit_price, discount_pct: c.discount_pct,
          modifier_ids: c.modifier_ids,
        })),
      });
      message.success(`Order ${res.data.order_number} created — Total: ${res.data.total}`);
      setCart([]);
      setSelectedTable('');
      setOrderNotes('');
      loadPOS();
    } catch { message.error('Failed to create order'); }
  };

  const payOrder = async (orderId: string) => {
    try {
      const order = activeOrders.find(o => o.id === orderId);
      const res = await api.payOrder(orderId, { payment_method: 'cash', paid_amount: order?.total || 0 });
      message.success(`Paid! Change: ${res.data.change}`);
      loadPOS();
    } catch { message.error('Payment failed'); }
  };

  /* ═══════════════════════════════════════════════════
     TAB: DASHBOARD
     ═══════════════════════════════════════════════════ */

  const renderDashboard = () => {
    if (!dashData) return <Spin size="large" />;
    const d = dashData.today;
    return (
      <div>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}><Card><Statistic title="Orders" value={d.orders} prefix={<ShoppingCartOutlined />} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Revenue" value={d.revenue} precision={2} prefix={<DollarOutlined />} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Open Orders" value={d.open_orders} prefix={<ClockCircleOutlined />} valueStyle={{ color: d.open_orders > 0 ? '#faad14' : '#52c41a' }} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Kitchen Pending" value={d.kitchen_pending} prefix={<FireOutlined />} valueStyle={{ color: d.kitchen_pending > 5 ? '#ff4d4f' : '#1890ff' }} /></Card></Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6}><Card><Statistic title="Tables" value={`${d.tables_occupied}/${d.tables_total}`} prefix={<AppstoreOutlined />} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Reservations" value={d.reservations} prefix={<UserOutlined />} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Waste Cost" value={d.waste_cost} precision={2} prefix={<WarningOutlined />} valueStyle={{ color: d.waste_cost > 100 ? '#ff4d4f' : '#333' }} /></Card></Col>
          <Col xs={12} sm={6}><Card>
            <Statistic title="Occupancy" value={d.tables_total > 0 ? Math.round(d.tables_occupied / d.tables_total * 100) : 0} suffix="%" prefix={<ShopOutlined />}
              valueStyle={{ color: d.tables_occupied / d.tables_total > 0.8 ? '#ff4d4f' : '#52c41a' }} />
          </Card></Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title="Revenue Breakdown" size="small">
              {revenueByType.length > 0 ? revenueByType.map((r: any) => (
                <Tag key={r.type} color={r.type === 'dine_in' ? 'blue' : r.type === 'takeaway' ? 'green' : 'orange'}>
                  {r.type}: {r.orders} orders — {r.revenue?.toFixed(2)} SAR
                </Tag>
              )) : <Text type="secondary">No data yet</Text>}
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  /* ═══════════════════════════════════════════════════
     TAB: FLOOR & TABLES
     ═══════════════════════════════════════════════════ */

  const renderFloor = () => {
    const statusColor: Record<string, string> = {
      available: '#52c41a', occupied: '#ff4d4f', reserved: '#faad14', cleaning: '#d9d9d9',
    };
    return (
      <div>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Space>
            {Object.entries(statusColor).map(([s, c]) => (
              <Tag key={s} color={c} style={{ fontSize: 12 }}>{s.toUpperCase()}</Tag>
            ))}
          </Space>
          <Button icon={<PlusOutlined />} onClick={() => setShowTableModal(true)}>Add Table</Button>
        </div>
        <Row gutter={[16, 16]}>
          {tables.map((t: any) => (
            <Col key={t.id} xs={8} sm={6} md={4}>
              <Card
                hoverable
                style={{ borderLeft: `4px solid ${statusColor[t.status] || '#d9d9d9'}`, textAlign: 'center' }}
                size="small"
                actions={[
                  t.status === 'available' && <Tag color="green" key="seat" style={{ cursor: 'pointer' }} onClick={() => api.updateTableStatus(t.id, 'occupied').then(loadFloor)}>Seat</Tag>,
                  t.status === 'occupied' && <Tag color="orange" key="clean" style={{ cursor: 'pointer' }} onClick={() => api.updateTableStatus(t.id, 'cleaning').then(loadFloor)}>Clean</Tag>,
                  t.status === 'cleaning' && <Tag color="blue" key="ready" style={{ cursor: 'pointer' }} onClick={() => api.updateTableStatus(t.id, 'available').then(loadFloor)}>Ready</Tag>,
                ].filter(Boolean)}
              >
                <Title level={4} style={{ margin: 0 }}>{t.table_number}</Title>
                <Text type="secondary">{t.capacity} seats</Text>
                {t.section && <><br /><Text type="secondary" style={{ fontSize: 11 }}>{t.section}</Text></>}
              </Card>
            </Col>
          ))}
          {tables.length === 0 && <Col span={24}><Empty description="No tables configured" /></Col>}
        </Row>

        <Modal title="Add Table" open={showTableModal} onCancel={() => setShowTableModal(false)}
          onOk={() => {
            tableForm.validateFields().then(v => {
              api.createTable(v).then(() => { message.success('Table created'); setShowTableModal(false); tableForm.resetFields(); loadFloor(); });
            });
          }}>
          <Form form={tableForm} layout="vertical">
            <Form.Item name="table_number" label="Table Number" rules={[{ required: true }]}>
              <Input placeholder="e.g., T1" />
            </Form.Item>
            <Form.Item name="section_id" label="Section">
              <Select allowClear placeholder="Select section">
                {sections.map((s: any) => <Select.Option key={s.id} value={s.id}>{s.name}</Select.Option>)}
              </Select>
            </Form.Item>
            <Form.Item name="capacity" label="Capacity" initialValue={4}>
              <InputNumber min={1} max={20} />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    );
  };

  /* ═══════════════════════════════════════════════════
     TAB: POS & ORDERS
     ═══════════════════════════════════════════════════ */

  const renderPOS = () => (
    <Row gutter={16}>
      {/* Left: Menu Items */}
      <Col xs={24} lg={14}>
        <Card title="Menu" size="small" extra={
          <Select value={selectedCategory || ''} onChange={setSelectedCategory} style={{ width: 150 }} allowClear placeholder="All categories">
            <Select.Option value="">All</Select.Option>
            {menuCategories.map((c: any) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
          </Select>
        }>
          <Row gutter={[8, 8]}>
            {menuItems.filter(i => i.available).map((item: any) => (
              <Col key={item.id} xs={12} sm={8} md={6}>
                <Card hoverable size="small" onClick={() => addToCart(item)} style={{ cursor: 'pointer' }}>
                  <Text strong style={{ fontSize: 12 }}>{item.name}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 11 }}>{item.category}</Text>
                  <br />
                  <Text style={{ fontSize: 14, fontWeight: 600, color: '#1890ff' }}>{item.price?.toFixed(2)}</Text>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      </Col>

      {/* Right: Cart */}
      <Col xs={24} lg={10}>
        <Card title={`Cart (${cart.length})`} size="small"
          extra={<Space>
            <Select value={orderType} onChange={setOrderType} style={{ width: 110 }}>
              <Select.Option value="dine_in">Dine In</Select.Option>
              <Select.Option value="takeaway">Takeaway</Select.Option>
              <Select.Option value="delivery">Delivery</Select.Option>
            </Select>
          </Space>}
        >
          {cart.length === 0 ? <Empty description="Empty cart" /> : (
            <>
              {cart.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <div style={{ flex: 1 }}>
                    <Text strong style={{ fontSize: 12 }}>{item.name}</Text>
                  </div>
                  <Space size={4}>
                    <InputNumber size="small" value={item.qty} min={1} max={99}
                      onChange={v => updateCartQty(idx, v || 1)} style={{ width: 50 }} />
                    <Text style={{ fontSize: 12, width: 60, textAlign: 'right' }}>{item.line_total?.toFixed(2)}</Text>
                    <Button size="small" type="text" danger icon={<DeleteOutlined />}
                      onClick={() => setCart(cart.filter((_, i) => i !== idx))} />
                  </Space>
                </div>
              ))}
              <Divider style={{ margin: '8px 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>Subtotal:</Text><Text>{cartTotal.toFixed(2)}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>VAT 15%:</Text><Text>{cartTax.toFixed(2)}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text strong style={{ fontSize: 16 }}>Total:</Text>
                <Text strong style={{ fontSize: 16, color: '#1890ff' }}>{(cartTotal + cartTax).toFixed(2)}</Text>
              </div>
              <Form.Item label="Notes" style={{ marginTop: 8 }}>
                <Input.TextArea rows={2} value={orderNotes} onChange={e => setOrderNotes(e.target.value)} placeholder="Order notes..." />
              </Form.Item>
              <Button type="primary" block size="large" onClick={submitOrder}>
                Place Order — {(cartTotal + cartTax).toFixed(2)} SAR
              </Button>
            </>
          )}
        </Card>

        {/* Active Orders */}
        <Card title={`Active Orders (${activeOrders.length})`} size="small" style={{ marginTop: 16 }}>
          {activeOrders.length === 0 ? <Text type="secondary">No active orders</Text> : (
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              {activeOrders.map((o: any) => (
                <Card key={o.id} size="small" style={{ borderLeft: `3px solid ${o.kitchen_status === 'ready' ? '#52c41a' : '#1890ff'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                      <Text strong>{o.order_number}</Text> — <Text>{o.type}</Text>
                      {o.table_id && <Tag color="blue" style={{ marginLeft: 4 }}>Table</Tag>}
                      <br />
                      <Text type="secondary">{o.total?.toFixed(2)} SAR — {o.guests} guests</Text>
                    </div>
                    <Space>
                      {o.status === 'open' && <Button size="small" icon={<FireOutlined />} onClick={() => api.sendToKitchen(o.id).then(loadPOS)}>Send to Kitchen</Button>}
                      {o.status !== 'paid' && o.status !== 'voided' && <Button size="small" type="primary" onClick={() => payOrder(o.id)}>Pay</Button>}
                    </Space>
                  </div>
                  <Tag color={o.kitchen_status === 'ready' ? 'green' : o.kitchen_status === 'fired' ? 'orange' : 'default'}>
                    Kitchen: {o.kitchen_status}
                  </Tag>
                </Card>
              ))}
            </Space>
          )}
        </Card>
      </Col>
    </Row>
  );

  /* ═══════════════════════════════════════════════════
     TAB: KITCHEN (KDS)
     ═══════════════════════════════════════════════════ */

  const renderKitchen = () => {
    const statusColor: Record<string, string> = {
      pending: 'default', fired: 'orange', started: 'blue', done: 'green',
    };
    return (
      <div>
        <div style={{ marginBottom: 16 }}>
          <Space>
            {kitchenStations.map((s: any) => (
              <Tag key={s.id} color="blue">{s.name} ({s.code})</Tag>
            ))}
          </Space>
        </div>
        {kitchenOrders.length === 0 ? <Empty description="No kitchen orders" /> : (
          <Row gutter={[12, 12]}>
            {kitchenOrders.map((ko: any) => (
              <Col key={ko.id} xs={24} sm={12} md={8} lg={6}>
                <Card size="small"
                  style={{ borderLeft: `4px solid ${statusColor[ko.status] === 'done' ? '#52c41a' : statusColor[ko.status] === 'started' ? '#1890ff' : '#faad14'}` }}
                  actions={[
                    ko.status === 'fired' && <Button size="small" type="primary" onClick={() => api.startKitchenOrder(ko.id).then(loadKitchen)}>Start</Button>,
                    ko.status === 'started' && <Button size="small" type="primary" ghost onClick={() => api.completeKitchenOrder(ko.id).then(loadKitchen)}>Done</Button>,
                  ].filter(Boolean)}
                >
                  <div style={{ textAlign: 'center' }}>
                    <Title level={4} style={{ margin: 0, color: ko.table ? '#1890ff' : undefined }}>
                      {ko.table || '—'}
                    </Title>
                    <Text type="secondary">{ko.order_number}</Text>
                    <Divider style={{ margin: '4px 0' }} />
                    <Text strong style={{ fontSize: 14 }}>{ko.item}</Text>
                    <br />
                    <Text style={{ fontSize: 20, fontWeight: 700 }}>x{ko.qty}</Text>
                    <br />
                    <Tag color={statusColor[ko.status]} style={{ marginTop: 4 }}>{ko.status.toUpperCase()}</Tag>
                    <br />
                    {ko.started_at && <Text type="secondary" style={{ fontSize: 10 }}>Started: {ko.started_at}</Text>}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </div>
    );
  };

  /* ═══════════════════════════════════════════════════
     TAB: MENU MANAGEMENT
     ═══════════════════════════════════════════════════ */

  const renderMenu = () => (
    <>
    <Tabs items={[
      {
        key: 'items', label: 'Menu Items',
        children: (
          <>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={() => setShowCategoryModal(true)}>+ Category</Button>
              <Button type="primary" onClick={() => setShowItemModal(true)}>+ Menu Item</Button>
            </div>
            <Table dataSource={menuItems} rowKey="id" size="small" pagination={{ pageSize: 20 }}
              columns={[
                { title: 'Code', dataIndex: 'code', width: 80 },
                { title: 'Name', dataIndex: 'name' },
                { title: 'Category', dataIndex: 'category' },
                { title: 'Price', dataIndex: 'price', render: (v: number) => `${v?.toFixed(2)}` },
                { title: 'Cost', dataIndex: 'cost', render: (v: number) => `${v?.toFixed(2)}` },
                { title: 'Station', dataIndex: 'kitchen_station' },
                { title: 'Available', dataIndex: 'available', render: (v: boolean, r: any) =>
                  <Tag color={v ? 'green' : 'red'} style={{ cursor: 'pointer' }}
                    onClick={() => api.toggleAvailability(r.id).then(loadMenuMgmt)}>
                    {v ? 'Yes' : 'No'}
                  </Tag>
                },
              ]}
            />
          </>
        ),
      },
      {
        key: 'recipes', label: 'Recipes',
        children: (
          <>
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" onClick={() => setShowRecipeModal(true)}>+ Recipe</Button>
            </div>
            <Table dataSource={recipes} rowKey="id" size="small"
              columns={[
                { title: 'Recipe', dataIndex: 'recipe_name' },
                { title: 'Menu Item', dataIndex: 'menu_item' },
                { title: 'Yield', dataIndex: 'yield_qty', render: (v: number, r: any) => `${v} ${r.yield_unit}` },
                { title: 'Total Cost', dataIndex: 'total_cost', render: (v: number) => `${v?.toFixed(2)}` },
                { title: 'Cost/Portion', dataIndex: 'cost_per_portion', render: (v: number) => `${v?.toFixed(2)}` },
                { title: 'Status', dataIndex: 'status', render: (v: string) => <Tag color={v === 'active' ? 'green' : 'default'}>{v}</Tag> },
              ]}
            />
          </>
        ),
      },
      {
        key: 'categories', label: 'Categories',
        children: (
          <Table dataSource={menuCategories} rowKey="id" size="small"
            columns={[
              { title: 'Name', dataIndex: 'name' },
              { title: 'Arabic', dataIndex: 'name_ar' },
              { title: 'Order', dataIndex: 'sort_order' },
              { title: 'Status', dataIndex: 'status', render: (v: string) => <Tag color={v === 'active' ? 'green' : 'default'}>{v}</Tag> },
            ]}
          />
        ),
      },
      {
        key: 'combos', label: 'Combos',
        children: (
          <Table dataSource={[]} rowKey="id" size="small"
            columns={[
              { title: 'Name', dataIndex: 'name' },
              { title: 'Price', dataIndex: 'price' },
              { title: 'Status', dataIndex: 'active' },
            ]}
            locale={{ emptyText: 'No combos configured' }}
          />
        ),
      },
    ]} />

    {/* Category Modal */}
    <Modal title="Add Category" open={showCategoryModal} onCancel={() => setShowCategoryModal(false)}
      onOk={() => {
        catForm.validateFields().then(v => {
          api.createMenuCategory(v).then(() => { message.success('Category created'); setShowCategoryModal(false); catForm.resetFields(); loadMenuMgmt(); });
        });
      }}>
      <Form form={catForm} layout="vertical">
        <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="name_ar" label="Arabic Name"><Input /></Form.Item>
        <Form.Item name="sort_order" label="Sort Order" initialValue={0}><InputNumber /></Form.Item>
      </Form>
    </Modal>

    {/* Menu Item Modal */}
    <Modal title="Add Menu Item" open={showItemModal} onCancel={() => setShowItemModal(false)} width={600}
      onOk={() => {
        itemForm.validateFields().then(v => {
          api.createMenuItem(v).then(() => { message.success('Menu item created'); setShowItemModal(false); itemForm.resetFields(); loadMenuMgmt(); });
        });
      }}>
      <Form form={itemForm} layout="vertical">
        <Row gutter={16}>
          <Col span={12}><Form.Item name="item_code" label="Code" rules={[{ required: true }]}><Input /></Form.Item></Col>
          <Col span={12}><Form.Item name="category_id" label="Category">
            <Select>{menuCategories.map((c: any) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}</Select>
          </Form.Item></Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}><Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item></Col>
          <Col span={12}><Form.Item name="name_ar" label="Arabic Name"><Input /></Form.Item></Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}><Form.Item name="selling_price" label="Price" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={8}><Form.Item name="cost_price" label="Cost"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={8}><Form.Item name="prep_time_minutes" label="Prep (min)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
        </Row>
        <Form.Item name="kitchen_station" label="Kitchen Station">
          <Select allowClear>
            {kitchenStations.map((s: any) => <Select.Option key={s.id} value={s.code}>{s.name}</Select.Option>)}
          </Select>
        </Form.Item>
      </Form>
    </Modal>

    {/* Recipe Modal */}
    <Modal title="Add Recipe" open={showRecipeModal} onCancel={() => setShowRecipeModal(false)} width={600}
      onOk={() => {
        recipeForm.validateFields().then(v => {
          api.createRecipe(v).then(() => { message.success('Recipe created'); setShowRecipeModal(false); recipeForm.resetFields(); loadMenuMgmt(); });
        });
      }}>
      <Form form={recipeForm} layout="vertical">
        <Form.Item name="menu_item_id" label="Menu Item" rules={[{ required: true }]}>
          <Select>{menuItems.map((m: any) => <Select.Option key={m.id} value={m.id}>{m.name}</Select.Option>)}</Select>
        </Form.Item>
        <Row gutter={16}>
          <Col span={12}><Form.Item name="yield_qty" label="Yield Qty" initialValue={1}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={12}><Form.Item name="yield_unit" label="Yield Unit" initialValue="portion"><Input /></Form.Item></Col>
        </Row>
        <Form.Item name="instructions" label="Instructions"><Input.TextArea rows={2} /></Form.Item>
      </Form>
    </Modal>
    </>
  );

  /* ═══════════════════════════════════════════════════
     TAB: INVENTORY & WASTE
     ═══════════════════════════════════════════════════ */

  const renderInventory = () => (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setShowWasteModal(true)}>+ Record Waste</Button>
      </div>
      <Table dataSource={wasteList} rowKey="id" size="small"
        columns={[
          { title: 'Number', dataIndex: 'number' },
          { title: 'Date', dataIndex: 'date' },
          { title: 'Type', dataIndex: 'type' },
          { title: 'Reason', dataIndex: 'reason' },
          { title: 'Total Cost', dataIndex: 'total_cost', render: (v: number) => `${v?.toFixed(2)} SAR` },
          { title: 'Status', dataIndex: 'status', render: (v: string) => <Tag>{v}</Tag> },
        ]}
      />

      <Modal title="Record Waste" open={showWasteModal} onCancel={() => setShowWasteModal(false)}
        onOk={() => {
          wasteForm.validateFields().then(v => {
            api.createWaste({ ...v, items: v.items || [] }).then(() => {
              message.success('Waste recorded'); setShowWasteModal(false); wasteForm.resetFields(); loadInventory();
            });
          });
        }}>
        <Form form={wasteForm} layout="vertical">
          <Form.Item name="waste_type" label="Type" initialValue="production">
            <Select>
              <Select.Option value="production">Production</Select.Option>
              <Select.Option value="expired">Expired</Select.Option>
              <Select.Option value="spoiled">Spoiled</Select.Option>
              <Select.Option value="other">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="reason" label="Reason"><Input /></Form.Item>
          <Form.Item name="notes" label="Notes"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );

  /* ═══════════════════════════════════════════════════
     TAB: CASH DRAWER
     ═══════════════════════════════════════════════════ */

  const renderCash = () => {
    const todayDrawer = cashDrawer.find((d: any) => d.status === 'open');
    return (
      <div>
        <Row gutter={16}>
          <Col span={8}>
            <Card title="Today's Drawer" size="small">
              {todayDrawer ? (
                <>
                  <Statistic title="Opening" value={todayDrawer.opening} prefix={<DollarOutlined />} />
                  <Divider />
                  <Button type="primary" onClick={() => {
                    Modal.confirm({
                      title: 'Close Cash Drawer',
                      content: 'Enter closing amount:',
                      onOk: () => api.closeCashDrawer({ closing_amount: todayDrawer.opening + 100 }).then(loadCash),
                    });
                  }}>Close Drawer</Button>
                </>
              ) : (
                <>
                  <Text type="secondary">No open drawer</Text>
                  <br />
                  <Button type="primary" style={{ marginTop: 8 }} onClick={() => {
                    Modal.confirm({
                      title: 'Open Cash Drawer',
                      content: 'Enter opening amount:',
                      onOk: () => api.openCashDrawer({ opening_amount: 500 }).then(loadCash),
                    });
                  }}>Open Drawer</Button>
                </>
              )}
            </Card>
          </Col>
          <Col span={16}>
            <Card title="Drawer History" size="small">
              <Table dataSource={cashDrawer} rowKey="id" size="small" pagination={{ pageSize: 10 }}
                columns={[
                  { title: 'Date', dataIndex: 'date' },
                  { title: 'Opening', dataIndex: 'opening', render: (v: number) => v?.toFixed(2) },
                  { title: 'Closing', dataIndex: 'closing', render: (v: number) => v?.toFixed(2) },
                  { title: 'Expected', dataIndex: 'expected', render: (v: number) => v?.toFixed(2) },
                  { title: 'Variance', dataIndex: 'variance', render: (v: number) => (
                    <Text style={{ color: v && v !== 0 ? '#ff4d4f' : '#52c41a' }}>{v?.toFixed(2)}</Text>
                  )},
                  { title: 'Status', dataIndex: 'status', render: (v: string) => <Tag color={v === 'open' ? 'green' : 'default'}>{v}</Tag> },
                ]}
              />
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  /* ═══════════════════════════════════════════════════
     TAB: ANALYTICS
     ═══════════════════════════════════════════════════ */

  const renderAnalytics = () => (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={12}>
        <Card title="Popular Items" size="small">
          <Table dataSource={popularItems} rowKey="name" size="small" pagination={false}
            columns={[
              { title: 'Item', dataIndex: 'name' },
              { title: 'Qty Sold', dataIndex: 'qty_sold' },
              { title: 'Revenue', dataIndex: 'revenue', render: (v: number) => `${v?.toFixed(2)} SAR` },
            ]}
          />
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card title="Revenue by Type" size="small">
          {revenueByType.map((r: any) => (
            <div key={r.type} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
              <Tag color={r.type === 'dine_in' ? 'blue' : r.type === 'takeaway' ? 'green' : 'orange'}>{r.type}</Tag>
              <Text>{r.orders} orders</Text>
              <Text strong>{r.revenue?.toFixed(2)} SAR</Text>
            </div>
          ))}
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card title="Food Cost Analysis" size="small">
          <Table dataSource={foodCostData} rowKey="menu_item" size="small" pagination={false}
            columns={[
              { title: 'Menu Item', dataIndex: 'menu_item' },
              { title: 'Cost', dataIndex: 'cost_per_portion', render: (v: number) => `${v?.toFixed(2)}` },
              { title: 'Price', dataIndex: 'selling_price', render: (v: number) => `${v?.toFixed(2)}` },
              { title: 'Food Cost %', dataIndex: 'food_cost_pct', render: (v: number) => (
                <Progress percent={v} size="small" status={v > 35 ? 'exception' : 'normal'} />
              )},
            ]}
          />
        </Card>
      </Col>
    </Row>
  );

  /* ═══════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════ */

  return (
    <div style={{ padding: 0 }}>
      <Tabs activeKey={activeTab} onChange={setActiveTab} size="large"
        items={[
          { key: 'dashboard', label: <span><DashboardOutlined /> Dashboard</span>, children: renderDashboard() },
          { key: 'floor', label: <span><AppstoreOutlined /> Floor</span>, children: renderFloor() },
          { key: 'pos', label: <span><ShoppingCartOutlined /> POS & Orders</span>, children: renderPOS() },
          { key: 'kitchen', label: <span><FireOutlined /> Kitchen KDS</span>, children: renderKitchen() },
          { key: 'menu', label: <span><MenuOutlined /> Menu & Recipes</span>, children: renderMenu() },
          { key: 'inventory', label: <span><ShopOutlined /> Inventory</span>, children: renderInventory() },
          { key: 'cash', label: <span><DollarOutlined /> Cash</span>, children: renderCash() },
          { key: 'analytics', label: <span><BarChartOutlined /> Analytics</span>, children: renderAnalytics() },
        ]}
      />
    </div>
  );
};

export default RestaurantPage;
