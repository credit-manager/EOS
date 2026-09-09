/**
 * Manufacturing ERP Professional — Workspace
 * Built on Commerce Engine + Core Platform
 * Tabs: Dashboard → BOM → Work Centers → Routings → Orders → Materials → Quality → Costs
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Typography, Space, Spin, Button, Tag, Table, Statistic,
  Tabs, Modal, Form, Input, Select, message, InputNumber, Empty,
} from 'antd';
import {
  DashboardOutlined, ToolOutlined, ApartmentOutlined,
  BuildOutlined, OrderedListOutlined, InboxOutlined,
  CheckCircleOutlined, DollarOutlined, PlusOutlined,
  WarningOutlined, RocketOutlined, PauseCircleOutlined,
  ArrowUpOutlined, ArrowDownOutlined,
} from '@ant-design/icons';
import apiClient from '../services/apiClient';

const { Text, Title } = Typography;

/* ═══════════════════════════════════════════════════
   API Client
   ═══════════════════════════════════════════════════ */

const api = {
  dashboard: (): Promise<any> => apiClient.get('/manufacturing/dashboard'),
  // BOM
  bomList: (): Promise<any> => apiClient.get('/manufacturing/bom'),
  bomDetail: (id: string): Promise<any> => apiClient.get(`/manufacturing/bom/${id}`),
  createBom: (d: any): Promise<any> => apiClient.post('/manufacturing/bom', d),
  activateBom: (id: string): Promise<any> => apiClient.put(`/manufacturing/bom/${id}/activate`),
  // Work Centers
  workCenters: (): Promise<any> => apiClient.get('/manufacturing/work-centers'),
  createWorkCenter: (d: any): Promise<any> => apiClient.post('/manufacturing/work-centers', d),
  // Routings
  routings: (): Promise<any> => apiClient.get('/manufacturing/routings'),
  routingDetail: (id: string): Promise<any> => apiClient.get(`/manufacturing/routings/${id}`),
  createRouting: (d: any): Promise<any> => apiClient.post('/manufacturing/routings', d),
  // Production Orders
  orders: (status?: string): Promise<any> => apiClient.get('/manufacturing/orders', { params: status ? { status } : {} }),
  orderDetail: (id: string): Promise<any> => apiClient.get(`/manufacturing/orders/${id}`),
  createOrder: (d: any): Promise<any> => apiClient.post('/manufacturing/orders', d),
  releaseOrder: (id: string): Promise<any> => apiClient.put(`/manufacturing/orders/${id}/release`),
  startOrder: (id: string): Promise<any> => apiClient.put(`/manufacturing/orders/${id}/start`),
  completeOrder: (id: string, qty: number): Promise<any> => apiClient.put(`/manufacturing/orders/${id}/complete?qty_completed=${qty}`),
  // Material Issues
  materialIssues: (): Promise<any> => apiClient.get('/manufacturing/material-issues'),
  createMaterialIssue: (d: any): Promise<any> => apiClient.post('/manufacturing/material-issues', d),
  issueMaterials: (id: string): Promise<any> => apiClient.put(`/manufacturing/material-issues/${id}/issue`),
  // Quality
  inspections: (result?: string): Promise<any> => apiClient.get('/manufacturing/quality-inspections', { params: result ? { result } : {} }),
  createInspection: (d: any): Promise<any> => apiClient.post('/manufacturing/quality-inspections', d),
  // Scrap
  createScrap: (d: any): Promise<any> => apiClient.post('/manufacturing/scrap', d),
  // Costs
  costs: (orderId: string): Promise<any> => apiClient.get(`/manufacturing/costs/${orderId}`),
  addCost: (d: any): Promise<any> => apiClient.post('/manufacturing/costs', d),
  // Items (from Trading)
  items: (): Promise<any> => apiClient.get('/trading/items'),
  warehouses: (): Promise<any> => apiClient.get('/trading/warehouses'),
};

/* ═══════════════════════════════════════════════════
   STATUS HELPERS
   ═══════════════════════════════════════════════════ */

const ORDER_STATUS: Record<string, { color: string; icon: any }> = {
  planned: { color: 'blue', icon: <PauseCircleOutlined /> },
  released: { color: 'orange', icon: <RocketOutlined /> },
  in_progress: { color: 'processing', icon: <ToolOutlined /> },
  completed: { color: 'success', icon: <CheckCircleOutlined /> },
  cancelled: { color: 'default', icon: <WarningOutlined /> },
};

const QC_RESULT: Record<string, string> = {
  pending: 'gold', passed: 'green', failed: 'red', partial: 'orange',
};

/* ═══════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════ */

const ManufacturingPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('dashboard');

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.dashboard();
      setDashboard(r.data || r);
    } catch { message.error('Failed to load dashboard'); }
    setLoading(false);
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  return (
    <div style={{ padding: 0 }}>
      <Title level={3} style={{ marginBottom: 16 }}>
        <ToolOutlined /> Manufacturing ERP
      </Title>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        { key: 'dashboard', label: <span><DashboardOutlined /> Dashboard</span>, children: <DashboardTab loading={loading} data={dashboard} /> },
        { key: 'bom', label: <span><ApartmentOutlined /> BOM</span>, children: <BOMTab /> },
        { key: 'workcenters', label: <span><BuildOutlined /> Work Centers</span>, children: <WorkCentersTab /> },
        { key: 'routings', label: <span><ToolOutlined /> Routings</span>, children: <RoutingsTab /> },
        { key: 'orders', label: <span><OrderedListOutlined /> Orders</span>, children: <OrdersTab /> },
        { key: 'materials', label: <span><InboxOutlined /> Materials</span>, children: <MaterialsTab /> },
        { key: 'quality', label: <span><CheckCircleOutlined /> Quality</span>, children: <QualityTab /> },
        { key: 'costs', label: <span><DollarOutlined /> Costs</span>, children: <CostsTab /> },
      ]} />
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: Dashboard
   ═══════════════════════════════════════════════════ */

const DashboardTab: React.FC<{ loading: boolean; data: any }> = ({ loading, data }) => {
  if (loading) return <Spin size="large" />;
  if (!data) return <Empty description="No data" />;
  const o = data.orders || {};
  const p = data.production || {};
  const pend = data.pending || {};
  const m = data.master_data || {};
  return (
    <Row gutter={[16, 16]}>
      <Col span={6}><Card><Statistic title="Planned Orders" value={o.planned || 0} valueStyle={{ color: '#1890ff' }} prefix={<PauseCircleOutlined />} /></Card></Col>
      <Col span={6}><Card><Statistic title="In Progress" value={o.in_progress || 0} valueStyle={{ color: '#faad14' }} prefix={<ToolOutlined />} /></Card></Col>
      <Col span={6}><Card><Statistic title="Completed" value={o.completed || 0} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} /></Card></Col>
      <Col span={6}><Card><Statistic title="Total Orders" value={o.total || 0} prefix={<OrderedListOutlined />} /></Card></Col>
      <Col span={6}><Card><Statistic title="Total Completed Qty" value={p.total_completed || 0} prefix={<ArrowUpOutlined />} /></Card></Col>
      <Col span={6}><Card><Statistic title="Total Scrapped" value={p.total_scrapped || 0} valueStyle={{ color: '#ff4d4f' }} prefix={<ArrowDownOutlined />} /></Card></Col>
      <Col span={6}><Card><Statistic title="Yield Rate" value={p.yield_rate || 100} suffix="%" valueStyle={{ color: (p.yield_rate || 100) >= 95 ? '#52c41a' : '#ff4d4f' }} /></Card></Col>
      <Col span={6}><Card><Statistic title="Pending Material Issues" value={pend.material_issues || 0} valueStyle={{ color: '#faad14' }} /></Card></Col>
      <Col span={4}><Card size="small"><Statistic title="BOMs" value={m.boms || 0} /></Card></Col>
      <Col span={4}><Card size="small"><Statistic title="Work Centers" value={m.work_centers || 0} /></Card></Col>
      <Col span={4}><Card size="small"><Statistic title="Routings" value={m.routings || 0} /></Card></Col>
      <Col span={4}><Card size="small"><Statistic title="Pending QI" value={pend.quality_inspections || 0} /></Card></Col>
      <Col span={4}><Card size="small"><Statistic title="Released" value={o.released || 0} /></Card></Col>
      <Col span={4}><Card size="small"><Statistic title="Planned Qty" value={p.total_planned || 0} /></Card></Col>
    </Row>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: BOM
   ═══════════════════════════════════════════════════ */

const BOMTab: React.FC = () => {
  const [boms, setBoms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [form] = Form.useForm();
  const [items, setItems] = useState<any[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [b, it] = await Promise.all([api.bomList(), api.items()]);
      setBoms(Array.isArray(b) ? b : b?.data || []);
      setItems(Array.isArray(it) ? it : it?.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.createBom(v);
      message.success('BOM created');
      setModal(false);
      form.resetFields();
      load();
    } catch (e: any) { if (e?.response?.data?.detail) message.error(e.response.data.detail); }
  };

  return (
    <Card title="Bill of Materials" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>New BOM</Button>}>
      <Table dataSource={boms} rowKey="id" loading={loading} size="small" columns={[
        { title: 'Code', dataIndex: 'bom_code', width: 120 },
        { title: 'Name', dataIndex: 'name' },
        { title: 'Revision', dataIndex: 'revision', width: 80 },
        { title: 'Status', dataIndex: 'status', width: 100, render: (s: string) => <Tag color={s === 'active' ? 'green' : s === 'draft' ? 'blue' : 'default'}>{s}</Tag> },
        { title: 'Version', dataIndex: 'version', width: 80 },
      ]} />
      <Modal title="Create BOM" open={modal} onOk={handleCreate} onCancel={() => setModal(false)} width={600}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="bom_code" label="BOM Code" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="item_id" label="Finished Good" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="children">{items.map((i: any) => <Select.Option key={i.id} value={i.id}>{i.name}</Select.Option>)}</Select>
            </Form.Item></Col>
            <Col span={12}><Form.Item name="revision" label="Revision" initialValue="A"><Input /></Form.Item></Col>
            <Col span={24}><Form.Item name="description" label="Description"><Input.TextArea rows={2} /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>
    </Card>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: Work Centers
   ═══════════════════════════════════════════════════ */

const WorkCentersTab: React.FC = () => {
  const [wcs, setWcs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.workCenters(); setWcs(Array.isArray(r) ? r : r?.data || []); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.createWorkCenter(v);
      message.success('Work center created');
      setModal(false);
      form.resetFields();
      load();
    } catch (e: any) { if (e?.response?.data?.detail) message.error(e.response.data.detail); }
  };

  return (
    <Card title="Work Centers" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>New Work Center</Button>}>
      <Table dataSource={wcs} rowKey="id" loading={loading} size="small" columns={[
        { title: 'Code', dataIndex: 'code', width: 120 },
        { title: 'Name', dataIndex: 'name' },
        { title: 'Type', dataIndex: 'work_center_type', width: 100, render: (t: string) => <Tag>{t}</Tag> },
        { title: 'Capacity/Hr', dataIndex: 'capacity_per_hour', width: 100 },
        { title: 'Cost/Hr', dataIndex: 'cost_per_hour', width: 100, render: (v: number) => `$${v}` },
        { title: 'Efficiency', dataIndex: 'efficiency_pct', width: 100, render: (v: number) => `${v}%` },
        { title: 'Status', dataIndex: 'status', width: 100, render: (s: string) => <Tag color={s === 'active' ? 'green' : 'default'}>{s}</Tag> },
      ]} />
      <Modal title="Create Work Center" open={modal} onOk={handleCreate} onCancel={() => setModal(false)} width={600}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="code" label="Code" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="work_center_type" label="Type" initialValue="machine">
              <Select><Select.Option value="machine">Machine</Select.Option><Select.Option value="labor">Labor</Select.Option><Select.Option value="both">Both</Select.Option></Select>
            </Form.Item></Col>
            <Col span={12}><Form.Item name="capacity_per_hour" label="Capacity/Hr" initialValue={1}><InputNumber min={0.01} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item name="cost_per_hour" label="Cost/Hr" initialValue={0}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item name="efficiency_pct" label="Efficiency %" initialValue={100}><InputNumber min={0} max={200} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>
    </Card>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: Routings
   ═══════════════════════════════════════════════════ */

const RoutingsTab: React.FC = () => {
  const [rts, setRts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.routings(); setRts(Array.isArray(r) ? r : r?.data || []); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <Card title="Production Routings">
      <Table dataSource={rts} rowKey="id" loading={loading} size="small" columns={[
        { title: 'Code', dataIndex: 'routing_code', width: 120 },
        { title: 'Name', dataIndex: 'name' },
        { title: 'Item', dataIndex: 'item_id', width: 200 },
        { title: 'Revision', dataIndex: 'revision', width: 80 },
        { title: 'Status', dataIndex: 'status', width: 100, render: (s: string) => <Tag color={s === 'active' ? 'green' : 'blue'}>{s}</Tag> },
      ]} />
    </Card>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: Production Orders
   ═══════════════════════════════════════════════════ */

const OrdersTab: React.FC = () => {
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [completeModal, setCompleteModal] = useState<{ id: string; max: number } | null>(null);
  const [form] = Form.useForm();
  const [compForm] = Form.useForm();
  const [items, setItems] = useState<any[]>([]);
  const [warehouses, setWarehouses] = useState<any[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o, it, wh] = await Promise.all([api.orders(), api.items(), api.warehouses()]);
      setOrders(Array.isArray(o) ? o : o?.data || []);
      setItems(Array.isArray(it) ? it : it?.data || []);
      setWarehouses(Array.isArray(wh) ? wh : wh?.data || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.createOrder(v);
      message.success('Order created');
      setModal(false);
      form.resetFields();
      load();
    } catch (e: any) { if (e?.response?.data?.detail) message.error(e.response.data.detail); }
  };

  const handleComplete = async () => {
    if (!completeModal) return;
    try {
      const v = await compForm.validateFields();
      await api.completeOrder(completeModal.id, v.qty);
      message.success('Order completed');
      setCompleteModal(null);
      compForm.resetFields();
      load();
    } catch (e: any) { if (e?.response?.data?.detail) message.error(e.response.data.detail); }
  };

  const doAction = async (action: string, id: string) => {
    try {
      if (action === 'release') await api.releaseOrder(id);
      else if (action === 'start') await api.startOrder(id);
      message.success(`Order ${action}d`);
      load();
    } catch (e: any) { if (e?.response?.data?.detail) message.error(e.response.data.detail); }
  };

  return (
    <Card title="Production Orders" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>New Order</Button>}>
      <Table dataSource={orders} rowKey="id" loading={loading} size="small" columns={[
        { title: 'Order #', dataIndex: 'order_number', width: 160 },
        { title: 'Status', dataIndex: 'status', width: 110, render: (s: string) => <Tag icon={ORDER_STATUS[s]?.icon} color={ORDER_STATUS[s]?.color}>{s}</Tag> },
        { title: 'Planned', dataIndex: 'qty_planned', width: 80 },
        { title: 'Completed', dataIndex: 'qty_completed', width: 80 },
        { title: 'Scrapped', dataIndex: 'qty_scrapped', width: 80 },
        { title: 'Priority', dataIndex: 'priority', width: 80 },
        { title: 'Start', dataIndex: 'planned_start', width: 100 },
        { title: 'End', dataIndex: 'planned_end', width: 100 },
        { title: 'Actions', width: 200, render: (_: any, r: any) => (
          <Space size="small">
            {r.status === 'planned' && <Button size="small" onClick={() => doAction('release', r.id)}>Release</Button>}
            {r.status === 'released' && <Button size="small" type="primary" onClick={() => doAction('start', r.id)}>Start</Button>}
            {r.status === 'in_progress' && <Button size="small" type="primary" onClick={() => setCompleteModal({ id: r.id, max: r.qty_planned })}>Complete</Button>}
          </Space>
        )},
      ]} />
      <Modal title="New Production Order" open={modal} onOk={handleCreate} onCancel={() => setModal(false)} width={600}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item name="item_id" label="Item" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="children">{items.map((i: any) => <Select.Option key={i.id} value={i.id}>{i.name}</Select.Option>)}</Select>
            </Form.Item></Col>
            <Col span={12}><Form.Item name="warehouse_id" label="Warehouse" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="children">{warehouses.map((w: any) => <Select.Option key={w.id} value={w.id}>{w.name}</Select.Option>)}</Select>
            </Form.Item></Col>
            <Col span={12}><Form.Item name="qty_planned" label="Qty" rules={[{ required: true }]}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item name="priority" label="Priority" initialValue={5}><InputNumber min={1} max={10} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item name="planned_start" label="Planned Start"><Input type="date" /></Form.Item></Col>
            <Col span={12}><Form.Item name="planned_end" label="Planned End"><Input type="date" /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>
      <Modal title="Complete Order" open={!!completeModal} onOk={handleComplete} onCancel={() => setCompleteModal(null)}>
        <Form form={compForm} layout="vertical">
          <Form.Item name="qty" label={`Qty to complete (max: ${completeModal?.max || 0})`} rules={[{ required: true }]}>
            <InputNumber min={1} max={completeModal?.max} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: Material Issues
   ═══════════════════════════════════════════════════ */

const MaterialsTab: React.FC = () => {
  const [issues, setIssues] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.materialIssues(); setIssues(Array.isArray(r) ? r : r?.data || []); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <Card title="Material Issues">
      <Table dataSource={issues} rowKey="id" loading={loading} size="small" columns={[
        { title: 'Issue #', dataIndex: 'issue_number', width: 160 },
        { title: 'Order', dataIndex: 'order_id', width: 200 },
        { title: 'Status', dataIndex: 'status', width: 100, render: (s: string) => <Tag color={s === 'completed' ? 'green' : s === 'pending' ? 'orange' : 'default'}>{s}</Tag> },
        { title: 'Warehouse', dataIndex: 'warehouse_id', width: 150 },
        { title: 'Issued At', dataIndex: 'issued_at', width: 160 },
      ]} />
    </Card>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: Quality
   ═══════════════════════════════════════════════════ */

const QualityTab: React.FC = () => {
  const [inspections, setInspections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.inspections(); setInspections(Array.isArray(r) ? r : r?.data || []); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <Card title="Quality Inspections">
      <Table dataSource={inspections} rowKey="id" loading={loading} size="small" columns={[
        { title: 'Inspection #', dataIndex: 'inspection_number', width: 160 },
        { title: 'Type', dataIndex: 'inspection_type', width: 100, render: (t: string) => <Tag>{t}</Tag> },
        { title: 'Inspected', dataIndex: 'qty_inspected', width: 100 },
        { title: 'Passed', dataIndex: 'qty_passed', width: 100, render: (v: number) => <Text type="success">{v}</Text> },
        { title: 'Failed', dataIndex: 'qty_failed', width: 100, render: (v: number) => v > 0 ? <Text type="danger">{v}</Text> : v },
        { title: 'Result', dataIndex: 'result', width: 100, render: (r: string) => <Tag color={QC_RESULT[r]}>{r}</Tag> },
        { title: 'Date', dataIndex: 'inspection_date', width: 120 },
      ]} />
    </Card>
  );
};

/* ═══════════════════════════════════════════════════
   TAB: Costs
   ═══════════════════════════════════════════════════ */

const CostsTab: React.FC = () => {
  const [orders, setOrders] = useState<any[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<string | null>(null);
  const [costs, setCosts] = useState<any>({ items: [], total_cost: 0 });
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [form] = Form.useForm();

  const loadOrders = useCallback(async () => {
    setLoading(true);
    try { const r = await api.orders(); setOrders(Array.isArray(r) ? r : r?.data || []); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { loadOrders(); }, [loadOrders]);

  const loadCosts = async (orderId: string) => {
    setSelectedOrder(orderId);
    try { const r = await api.costs(orderId); setCosts(r.data || r); } catch { setCosts({ items: [], total_cost: 0 }); }
  };

  const handleAddCost = async () => {
    try {
      const v = await form.validateFields();
      await api.addCost({ ...v, order_id: selectedOrder });
      message.success('Cost added');
      setModal(false);
      form.resetFields();
      loadCosts(selectedOrder!);
    } catch (e: any) { if (e?.response?.data?.detail) message.error(e.response.data.detail); }
  };

  return (
    <Card title="Production Costs">
      <Row gutter={16}>
        <Col span={10}>
          <Card size="small" title="Select Order">
            <Table dataSource={orders} rowKey="id" loading={loading} size="small" pagination={{ pageSize: 8 }}
              onRow={(r) => ({ onClick: () => loadCosts(r.id), style: { cursor: 'pointer', background: selectedOrder === r.id ? '#e6f7ff' : undefined } })}
              columns={[
                { title: 'Order #', dataIndex: 'order_number', width: 160 },
                { title: 'Status', dataIndex: 'status', width: 100 },
              ]}
            />
          </Card>
        </Col>
        <Col span={14}>
          <Card size="small" title={selectedOrder ? `Costs — ${selectedOrder.slice(0, 8)}...` : 'Select an order'}
            extra={selectedOrder && <Button size="small" icon={<PlusOutlined />} onClick={() => setModal(true)}>Add Cost</Button>}>
            {selectedOrder ? (
              <>
                <Statistic title="Total Cost" value={costs.total_cost || 0} prefix="$" style={{ marginBottom: 16 }} />
                <Table dataSource={costs.items || []} rowKey="id" size="small" pagination={false} columns={[
                  { title: 'Type', dataIndex: 'cost_type', width: 100, render: (t: string) => <Tag>{t}</Tag> },
                  { title: 'Amount', dataIndex: 'amount', width: 100, render: (v: number) => `$${v}` },
                  { title: 'Description', dataIndex: 'description' },
                ]} />
              </>
            ) : <Empty description="Select an order to view costs" />}
          </Card>
        </Col>
      </Row>
      <Modal title="Add Cost" open={modal} onOk={handleAddCost} onCancel={() => setModal(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="cost_type" label="Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="material">Material</Select.Option>
              <Select.Option value="labor">Labor</Select.Option>
              <Select.Option value="overhead">Overhead</Select.Option>
              <Select.Option value="setup">Setup</Select.Option>
              <Select.Option value="scrap">Scrap</Select.Option>
              <Select.Option value="other">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="Amount" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="description" label="Description"><Input /></Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ManufacturingPage;
