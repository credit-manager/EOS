/**
 * Construction ERP Professional — Workspace
 * Projects → BOQ → Procurement → Stock → Equipment → Site Ops → Finance
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Row, Col, Typography, Space, Spin, Button, Tag, Table, Statistic,
  Tabs, Modal, Form, Input, Select, message, InputNumber, Badge, Empty,
  Divider, Descriptions, List, Alert, Tooltip,
} from 'antd';
import {
  ProjectOutlined, ShopOutlined, ShoppingCartOutlined, TeamOutlined,
  PlusOutlined, ReloadOutlined,
  CheckCircleOutlined, WarningOutlined,
  ArrowUpOutlined, DollarOutlined, BankOutlined,
  FileTextOutlined, ToolOutlined,
  EnvironmentOutlined, BarChartOutlined, AuditOutlined, DashboardOutlined,
} from '@ant-design/icons';
import apiClient from '../services/apiClient';

const { Text } = Typography;

/* ═══════════════════════════════════════════════════
   API Client — matches construction_api.py endpoints
   ═══════════════════════════════════════════════════ */

const api = {
  // Dashboard
  dashboard: () => apiClient.get('/construction/dashboard'),
  // Projects
  projects: (p?: any) => apiClient.get('/construction/projects', { params: p }),
  createProject: (d: any) => apiClient.post('/construction/projects', d),
  project: (id: string) => apiClient.get(`/construction/projects/${id}`),
  // BOQ
  boq: (pid: string) => apiClient.get(`/construction/projects/${pid}/boq`),
  addBoq: (pid: string, d: any) => apiClient.post(`/construction/projects/${pid}/boq`, d),
  // Procurement
  prList: () => apiClient.get('/construction/procurement/requests'),
  createPR: (d: any) => apiClient.post('/construction/procurement/requests', d),
  submitPR: (id: string) => apiClient.post(`/construction/procurement/requests/${id}/submit`),
  approvePR: (id: string) => apiClient.post(`/construction/procurement/requests/${id}/approve`),
  poList: () => apiClient.get('/construction/procurement/orders'),
  createPO: (d: any) => apiClient.post('/construction/procurement/orders', d),
  receivePO: (id: string, d: any) => apiClient.post(`/construction/procurement/orders/${id}/receive`, d),
  // Stock & Warehouses
  stock: () => apiClient.get('/construction/stock'),
  issueStock: (d: any) => apiClient.post('/construction/stock/issue', d),
  warehouses: () => apiClient.get('/construction/warehouses'),
  createWarehouse: (d: any) => apiClient.post('/construction/warehouses', d),
  // Equipment
  equipment: () => apiClient.get('/construction/equipment'),
  createEquipment: (d: any) => apiClient.post('/construction/equipment', d),
  logEquipment: (id: string, d: any) => apiClient.post(`/construction/equipment/${id}/log`, d),
  // Site Operations
  diaryList: () => apiClient.get('/construction/site/diary'),
  createDiary: (d: any) => apiClient.post('/construction/site/diary', d),
  rfiList: () => apiClient.get('/construction/site/rfi'),
  createRFI: (d: any) => apiClient.post('/construction/site/rfi', d),
  // Subcontractors
  subcontractors: () => apiClient.get('/construction/subcontractors'),
  createSubcontractor: (d: any) => apiClient.post('/construction/subcontractors', d),
  // Profitability
  profitability: (pid: string) => apiClient.get(`/construction/projects/${pid}/profitability`),
};

/* ═══════════════════════════════════════════════════
   Shared Components
   ═══════════════════════════════════════════════════ */

const KpiCard = ({ title, value, icon, color, suffix, sub }: any) => (
  <div style={{
    background: '#fff', borderRadius: 14, padding: '20px 22px',
    border: '1px solid #f0f0f0', position: 'relative', overflow: 'hidden',
    transition: 'box-shadow 0.2s',
  }}>
    <div style={{
      position: 'absolute', top: -20, right: -20, width: 80, height: 80,
      borderRadius: '50%', background: `${color}08`,
    }} />
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <div>
        <Text style={{ color: '#8c8c8c', fontSize: 12 }}>{title}</Text>
        <div style={{ fontSize: 26, fontWeight: 700, color: '#1a1a2e', marginTop: 4 }}>
          {typeof value === 'number' ? value.toLocaleString() : value}{suffix || ''}
        </div>
        {sub && <Text type="secondary" style={{ fontSize: 11 }}>{sub}</Text>}
      </div>
      <div style={{
        width: 40, height: 40, borderRadius: 10, background: `${color}10`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color, fontSize: 16,
      }}>{icon}</div>
    </div>
  </div>
);

const statusColor = (s: string) => {
  const m: Record<string, string> = {
    active: 'green', completed: 'blue', planning: 'purple', pending: 'orange',
    draft: 'default', approved: 'green', rejected: 'red', received: 'green',
    issued: 'blue', submitted: 'processing',
  };
  return m[s?.toLowerCase()] || 'default';
};

/* ═══════════════════════════════════════════════════
   Dashboard — Construction KPIs
   ═══════════════════════════════════════════════════ */

const DashboardTab: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await api.dashboard()); } catch { }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spin />;
  if (!data) return <Empty />;

  const k = data.kpis || {};
  const alerts = data.alerts || [];

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <KpiCard title="Total Projects" value={k.total_projects}
            icon={<ProjectOutlined />} color="#6366f1" sub={`${k.active_projects} active`} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="Contract Value" value={k.contract_value}
            icon={<DollarOutlined />} color="#22c55e" suffix=" SAR" />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="Actual Cost" value={k.actual_cost}
            icon={<BankOutlined />} color="#f59e0b" suffix=" SAR" />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="Gross Margin" value={k.gross_margin}
            icon={<ArrowUpOutlined />} color="#06b6d4" suffix="%"
            sub={`${(k.gross_profit || 0).toLocaleString()} SAR profit`} />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <KpiCard title="Pending PRs" value={k.pending_pr}
            icon={<FileTextOutlined />} color="#f97316" />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="Pending POs" value={k.pending_po}
            icon={<ShoppingCartOutlined />} color="#8b5cf6" />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="Low Stock Alerts" value={k.low_stock_alerts}
            icon={<WarningOutlined />} color="#ef4444" />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="Completed" value={k.completed_projects}
            icon={<CheckCircleOutlined />} color="#22c55e" />
        </Col>
      </Row>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card title="Alerts" size="small" style={{ borderRadius: 12, marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {alerts.map((a: any, i: number) => (
              <Alert key={i} type={a.type || 'info'} message={a.message} showIcon
                style={{ borderRadius: 8 }} />
            ))}
          </Space>
        </Card>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Projects — CRUD + BOQ + Profitability
   ═══════════════════════════════════════════════════ */

const ProjectsTab: React.FC = () => {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [createVisible, setCreateVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedProject, setSelectedProject] = useState<any>(null);
  const [boqVisible, setBoqVisible] = useState(false);
  const [boqData, setBoqData] = useState<any[]>([]);
  const [profitVisible, setProfitVisible] = useState(false);
  const [profitData, setProfitData] = useState<any>(null);
  const [form] = Form.useForm();
  const [boqForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { const r: any = await api.projects(); setProjects(r.data || []); } catch { }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (values: any) => {
    try {
      await api.createProject(values);
      message.success('Project created');
      setCreateVisible(false);
      form.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  const showDetail = async (id: string) => {
    try {
      const r: any = await api.project(id);
      setSelectedProject(r);
      setDetailVisible(true);
    } catch { }
  };

  const showBoq = async (pid: string) => {
    try {
      const r: any = await api.boq(pid);
      setBoqData(r.data || []);
      setSelectedProject({ ...selectedProject, id: pid });
      setBoqVisible(true);
    } catch { }
  };

  const handleAddBoq = async (values: any) => {
    try {
      await api.addBoq(selectedProject?.id, values);
      message.success('BOQ item added');
      boqForm.resetFields();
      showBoq(selectedProject?.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  const showProfit = async (pid: string) => {
    try {
      const r: any = await api.profitability(pid);
      setProfitData(r);
      setProfitVisible(true);
    } catch { }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 15 }}>Projects</Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}
            style={{ background: '#6366f1' }}>New Project</Button>
        </Space>
      </div>

      <Table
        dataSource={projects}
        columns={[
          { title: 'Code', dataIndex: 'code', width: 120,
            render: (v: string) => <Text code>{v}</Text> },
          { title: 'Project', key: 'name',
            render: (_: any, r: any) => (
              <a onClick={() => showDetail(r.id)} style={{ fontWeight: 500 }}>{r.name}</a>
            )},
          { title: 'Status', dataIndex: 'status', width: 110,
            render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
          { title: 'Budget', dataIndex: 'budget', width: 140,
            render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
          { title: 'Cost', dataIndex: 'actual_cost', width: 140,
            render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
          { title: 'Start', dataIndex: 'start_date', width: 110,
            render: (v: string) => v ? new Date(v).toLocaleDateString('en-GB') : '—' },
          { title: 'End', dataIndex: 'end_date', width: 110,
            render: (v: string) => v ? new Date(v).toLocaleDateString('en-GB') : '—' },
          { title: '', key: 'actions', width: 180,
            render: (_: any, r: any) => (
              <Space>
                <Tooltip title="BOQ"><Button size="small" icon={<BarChartOutlined />}
                  onClick={() => showBoq(r.id)} /></Tooltip>
                <Tooltip title="Profitability"><Button size="small" icon={<DollarOutlined />}
                  onClick={() => showProfit(r.id)} /></Tooltip>
              </Space>
            )},
        ]}
        rowKey="id"
        loading={loading}
        size="small"
        locale={{ emptyText: <Empty description="No projects yet" /> }}
      />

      {/* Create Project Modal */}
      <Modal title="New Project" open={createVisible} onCancel={() => setCreateVisible(false)}
        footer={null} width={560}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item name="name" label="Project Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Cairo Tower Phase 2" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="code" label="Code">
                <Input placeholder="Auto-generated" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="budget" label="Budget (SAR)">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="start_date" label="Start Date">
                <Input type="date" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="end_date" label="End Date">
                <Input type="date" />
              </Form.Item>
            </Col>
          </Row>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Create Project</Button>
        </Form>
      </Modal>

      {/* Project Detail Modal */}
      <Modal title={selectedProject?.name} open={detailVisible}
        onCancel={() => setDetailVisible(false)} footer={null} width={700}>
        {selectedProject && (
          <>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="Status">
                <Tag color={statusColor(selectedProject.status)}>{selectedProject.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="BOQ Items">{selectedProject.boq_items || 0}</Descriptions.Item>
              <Descriptions.Item label="Budget">
                {(selectedProject.budget || 0).toLocaleString()} SAR
              </Descriptions.Item>
              <Descriptions.Item label="BOQ Total">
                {(selectedProject.boq_total || 0).toLocaleString()} SAR
              </Descriptions.Item>
              <Descriptions.Item label="Actual Cost">
                {(selectedProject.actual_cost || 0).toLocaleString()} SAR
              </Descriptions.Item>
              <Descriptions.Item label="Variance">
                <Text type={selectedProject.variance >= 0 ? 'success' : 'danger'}>
                  {(selectedProject.variance || 0).toLocaleString()} SAR
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="Start">{selectedProject.start_date || '—'}</Descriptions.Item>
              <Descriptions.Item label="End">{selectedProject.end_date || '—'}</Descriptions.Item>
            </Descriptions>
            {selectedProject.description && (
              <div style={{ marginTop: 12 }}>
                <Text type="secondary">{selectedProject.description}</Text>
              </div>
            )}
          </>
        )}
      </Modal>

      {/* BOQ Modal */}
      <Modal title="Bill of Quantities" open={boqVisible}
        onCancel={() => setBoqVisible(false)} footer={null} width={800}>
        <Table dataSource={boqData} rowKey="id" size="small"
          columns={[
            { title: 'Item', dataIndex: 'item_number', width: 80 },
            { title: 'Description', dataIndex: 'description' },
            { title: 'Unit', dataIndex: 'unit', width: 60 },
            { title: 'Qty', dataIndex: 'quantity', width: 80, render: (v: number) => (v || 0).toLocaleString() },
            { title: 'Unit Price', dataIndex: 'unit_price', width: 110,
              render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
            { title: 'Amount', dataIndex: 'amount', width: 120,
              render: (v: number) => <Text strong>{(v || 0).toLocaleString()} SAR</Text> },
            { title: 'Completed', dataIndex: 'completed_qty', width: 80,
              render: (v: number) => `${(v || 0).toLocaleString()}` },
            { title: 'Status', dataIndex: 'status', width: 90,
              render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
          ]}
          locale={{ emptyText: <Empty description="No BOQ items" /> }}
          footer={() => (
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text strong>Total: {boqData.reduce((s, i) => s + (i.amount || 0), 0).toLocaleString()} SAR</Text>
            </div>
          )}
        />
        <Divider />
        <Form form={boqForm} layout="inline" onFinish={handleAddBoq}>
          <Form.Item name="item_number" rules={[{ required: true }]}>
            <Input placeholder="Item#" style={{ width: 70 }} />
          </Form.Item>
          <Form.Item name="description" rules={[{ required: true }]}>
            <Input placeholder="Description" style={{ width: 180 }} />
          </Form.Item>
          <Form.Item name="unit">
            <Input placeholder="Unit" style={{ width: 60 }} />
          </Form.Item>
          <Form.Item name="quantity">
            <InputNumber placeholder="Qty" style={{ width: 90 }} min={0} />
          </Form.Item>
          <Form.Item name="unit_price">
            <InputNumber placeholder="Price" style={{ width: 110 }} min={0} />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>Add</Button>
        </Form>
      </Modal>

      {/* Profitability Modal */}
      <Modal title="Project Profitability" open={profitVisible}
        onCancel={() => setProfitVisible(false)} footer={null} width={600}>
        {profitData && (
          <div>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Statistic title="Contract Value" value={profitData.contract_value || 0}
                  suffix="SAR" valueStyle={{ fontSize: 18, color: '#22c55e' }} />
              </Col>
              <Col span={8}>
                <Statistic title="Actual Cost" value={profitData.actual_cost || 0}
                  suffix="SAR" valueStyle={{ fontSize: 18, color: '#f59e0b' }} />
              </Col>
              <Col span={8}>
                <Statistic title="Variance" value={profitData.variance || 0}
                  suffix="SAR" valueStyle={{ fontSize: 18, color: profitData.variance >= 0 ? '#22c55e' : '#ef4444' }} />
              </Col>
            </Row>
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Statistic title="Gross Margin" value={profitData.gross_margin || 0}
                  suffix="%" valueStyle={{ fontSize: 20, fontWeight: 700 }} />
              </Col>
              <Col span={8}>
                <Statistic title="Earned Value" value={profitData.earned_value || 0}
                  suffix="SAR" valueStyle={{ fontSize: 16 }} />
              </Col>
              <Col span={8}>
                <Statistic title="Budget" value={profitData.budget || 0}
                  suffix="SAR" valueStyle={{ fontSize: 16 }} />
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Procurement — PR + PO with Approval Workflow
   ═══════════════════════════════════════════════════ */

const ProcurementTab: React.FC = () => {
  const [prList, setPrList] = useState<any[]>([]);
  const [poList, setPoList] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [prVisible, setPrVisible] = useState(false);
  const [poVisible, setPoVisible] = useState(false);
  const [receiveVisible, setReceiveVisible] = useState(false);
  const [selectedPO, setSelectedPO] = useState<any>(null);
  const [prForm] = Form.useForm();
  const [poForm] = Form.useForm();
  const [receiveForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pr, po, p]: any[] = await Promise.all([api.prList(), api.poList(), api.projects()]);
      setPrList(pr.data || []);
      setPoList(po.data || []);
      setProjects(p.data || []);
    } catch { }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreatePR = async (values: any) => {
    try {
      await api.createPR({
        ...values,
        items: [{ item_code: values.item_code, quantity: values.quantity, unit_price: values.unit_price }],
      });
      message.success('Purchase request created');
      setPrVisible(false);
      prForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  const handleCreatePO = async (values: any) => {
    try {
      await api.createPO({
        ...values,
        items: [{ item_code: values.item_code, quantity: values.quantity, unit_price: values.unit_price }],
      });
      message.success('Purchase order created');
      setPoVisible(false);
      poForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  const handleReceive = async (values: any) => {
    try {
      await api.receivePO(selectedPO?.id, {
        warehouse_id: values.warehouse_id,
        items: [{ item_code: values.item_code, quantity: values.quantity, unit_price: values.unit_price }],
      });
      message.success('Goods received, stock updated, journal posted');
      setReceiveVisible(false);
      receiveForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 15 }}>Procurement</Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} />
          <Button onClick={() => setPrVisible(true)}>Purchase Request</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setPoVisible(true)}
            style={{ background: '#6366f1' }}>Purchase Order</Button>
        </Space>
      </div>

      <Tabs items={[
        {
          key: 'pr',
          label: <Space>Requests <Badge count={prList.length} size="small" /></Space>,
          children: (
            <Table dataSource={prList} rowKey="id" size="small" loading={loading}
              columns={[
                { title: 'Number', dataIndex: 'pr_number', render: (v: string) => <Text code>{v}</Text> },
                { title: 'Description', dataIndex: 'description' },
                { title: 'Amount', dataIndex: 'total_amount', width: 130,
                  render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
                { title: 'Status', dataIndex: 'status', width: 100,
                  render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
                { title: '', key: 'actions', width: 140,
                  render: (_: any, r: any) => r.status === 'draft' ? (
                    <Space>
                      <Button size="small" onClick={async () => {
                        await api.submitPR(r.id); load();
                      }}>Submit</Button>
                      <Button size="small" type="primary" onClick={async () => {
                        await api.approvePR(r.id); load();
                      }}>Approve</Button>
                    </Space>
                  ) : null },
              ]}
              locale={{ emptyText: <Empty description="No purchase requests" /> }}
            />
          ),
        },
        {
          key: 'po',
          label: <Space>Orders <Badge count={poList.length} size="small" /></Space>,
          children: (
            <Table dataSource={poList} rowKey="id" size="small" loading={loading}
              columns={[
                { title: 'Number', dataIndex: 'po_number', render: (v: string) => <Text code>{v}</Text> },
                { title: 'Supplier', dataIndex: 'supplier_name' },
                { title: 'Amount', dataIndex: 'total_amount', width: 130,
                  render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
                { title: 'Date', dataIndex: 'po_date', width: 110,
                  render: (v: string) => v ? new Date(v).toLocaleDateString('en-GB') : '—' },
                { title: 'Delivery', dataIndex: 'delivery_date', width: 110,
                  render: (v: string) => v ? new Date(v).toLocaleDateString('en-GB') : '—' },
                { title: 'Status', dataIndex: 'status', width: 100,
                  render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
                { title: '', key: 'actions', width: 100,
                  render: (_: any, r: any) => r.status === 'pending' ? (
                    <Button size="small" type="primary" style={{ background: '#22c55e' }}
                      onClick={() => { setSelectedPO(r); setReceiveVisible(true); }}>
                      Receive
                    </Button>
                  ) : null },
              ]}
              locale={{ emptyText: <Empty description="No purchase orders" /> }}
            />
          ),
        },
      ]} />

      {/* Create PR Modal */}
      <Modal title="Purchase Request" open={prVisible}
        onCancel={() => setPrVisible(false)} footer={null}>
        <Form form={prForm} layout="vertical" onFinish={handleCreatePR}>
          <Form.Item name="project_id" label="Project" rules={[{ required: true }]}>
            <Select placeholder="Select project" showSearch optionFilterProp="label">
              {projects.map(p => <Select.Option key={p.id} value={p.id} label={p.name}>{p.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="description" label="Description" rules={[{ required: true }]}>
            <Input placeholder="What do you need?" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="item_code" label="Item Code"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="quantity" label="Qty"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_price" label="Price"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Submit Request</Button>
        </Form>
      </Modal>

      {/* Create PO Modal */}
      <Modal title="Purchase Order" open={poVisible}
        onCancel={() => setPoVisible(false)} footer={null} width={600}>
        <Form form={poForm} layout="vertical" onFinish={handleCreatePO}>
          <Form.Item name="supplier_name" label="Supplier" rules={[{ required: true }]}>
            <Input placeholder="Supplier name" />
          </Form.Item>
          <Form.Item name="project_id" label="Project">
            <Select placeholder="Select project" showSearch optionFilterProp="label">
              {projects.map(p => <Select.Option key={p.id} value={p.id} label={p.name}>{p.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="po_date" label="PO Date"><Input type="date" /></Form.Item></Col>
            <Col span={8}><Form.Item name="delivery_date" label="Delivery Date"><Input type="date" /></Form.Item></Col>
          </Row>
          <Divider>Items</Divider>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="item_code" label="Item Code"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="quantity" label="Qty"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_price" label="Price"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Create PO</Button>
        </Form>
      </Modal>

      {/* Receive Modal */}
      <Modal title={`Receive — ${selectedPO?.po_number || ''}`} open={receiveVisible}
        onCancel={() => setReceiveVisible(false)} footer={null}>
        <Form form={receiveForm} layout="vertical" onFinish={handleReceive}>
          <Form.Item name="warehouse_id" label="Warehouse" rules={[{ required: true }]}>
            <Input placeholder="WH-001" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="item_code" label="Item Code" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="quantity" label="Qty" rules={[{ required: true }]}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_price" label="Price" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" style={{ background: '#22c55e' }}>
            Receive & Post Journal
          </Button>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Stock & Warehouses
   ═══════════════════════════════════════════════════ */

const StockTab: React.FC = () => {
  const [stock, setStock] = useState<any[]>([]);
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [issueVisible, setIssueVisible] = useState(false);
  const [whVisible, setWhVisible] = useState(false);
  const [issueForm] = Form.useForm();
  const [whForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, w, p]: any[] = await Promise.all([api.stock(), api.warehouses(), api.projects()]);
      setStock(s.data || []);
      setWarehouses(w.data || []);
      setProjects(p.data || []);
    } catch { }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleIssue = async (values: any) => {
    try {
      await api.issueStock(values);
      message.success('Stock issued, journal posted');
      setIssueVisible(false);
      issueForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  const handleCreateWH = async (values: any) => {
    try {
      await api.createWarehouse(values);
      message.success('Warehouse created');
      setWhVisible(false);
      whForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 15 }}>Stock & Materials</Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} />
          <Button icon={<PlusOutlined />} onClick={() => setWhVisible(true)}>Warehouse</Button>
          <Button icon={<ShopOutlined />} style={{ background: '#f59e0b', color: '#fff' }}
            onClick={() => setIssueVisible(true)}>Issue to Project</Button>
        </Space>
      </div>

      <Table
        dataSource={stock}
        rowKey="id"
        loading={loading}
        size="small"
        columns={[
          { title: 'Item', key: 'item', width: 200,
            render: (_: any, r: any) => (
              <div>
                <Text strong style={{ fontSize: 13 }}>{r.item_name || r.item_code}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 11 }}>{r.item_code}</Text>
              </div>
            )},
          { title: 'Warehouse', dataIndex: 'warehouse_id', width: 100 },
          { title: 'On Hand', dataIndex: 'on_hand', width: 100,
            render: (v: number) => <Text strong>{(v || 0).toLocaleString()}</Text> },
          { title: 'Reserved', dataIndex: 'reserved', width: 80 },
          { title: 'Available', key: 'avail', width: 100,
            render: (_: any, r: any) => {
              const a = (r.on_hand || 0) - (r.reserved || 0);
              return <Text style={{ color: a > 0 ? '#22c55e' : '#ef4444' }}>{a.toLocaleString()}</Text>;
            }},
          { title: 'Min Stock', dataIndex: 'min_stock', width: 80 },
          { title: 'Unit Cost', dataIndex: 'unit_cost', width: 100,
            render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
          { title: 'Value', key: 'value', width: 120,
            render: (_: any, r: any) => {
              const val = (r.on_hand || 0) * (r.unit_cost || 0);
              return <Text strong>{val.toLocaleString()} SAR</Text>;
            }},
        ]}
        locale={{ emptyText: <Empty description="No stock records" /> }}
      />

      {/* Warehouses List */}
      {warehouses.length > 0 && (
        <Card title="Warehouses" size="small" style={{ borderRadius: 12, marginTop: 16 }}>
          <List dataSource={warehouses}
            renderItem={(item: any) => (
              <List.Item>
                <Text>{item.code}</Text> — <Text>{item.name}</Text>
                <Text type="secondary">{item.address}</Text>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Issue Modal */}
      <Modal title="Issue Material to Project" open={issueVisible}
        onCancel={() => setIssueVisible(false)} footer={null}>
        <Form form={issueForm} layout="vertical" onFinish={handleIssue}>
          <Form.Item name="item_code" label="Item Code" rules={[{ required: true }]}>
            <Input placeholder="e.g. STEEL-001" />
          </Form.Item>
          <Form.Item name="quantity" label="Quantity" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="project_id" label="Project" rules={[{ required: true }]}>
            <Select placeholder="Select project" showSearch optionFilterProp="label">
              {projects.map(p => <Select.Option key={p.id} value={p.id} label={p.name}>{p.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Button type="primary" htmlType="submit" style={{ background: '#f59e0b' }}>
            Issue & Post Journal
          </Button>
        </Form>
      </Modal>

      {/* Create Warehouse Modal */}
      <Modal title="New Warehouse" open={whVisible}
        onCancel={() => setWhVisible(false)} footer={null}>
        <Form form={whForm} layout="vertical" onFinish={handleCreateWH}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input placeholder="WH-002" />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="Warehouse name" />
          </Form.Item>
          <Form.Item name="address" label="Address">
            <Input />
          </Form.Item>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Create</Button>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Equipment
   ═══════════════════════════════════════════════════ */

const EquipmentTab: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [createVisible, setCreateVisible] = useState(false);
  const [logVisible, setLogVisible] = useState(false);
  const [selectedEq, setSelectedEq] = useState<any>(null);
  const [createForm] = Form.useForm();
  const [logForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { const r: any = await api.equipment(); setData(r.data || []); } catch { }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (values: any) => {
    try {
      await api.createEquipment(values);
      message.success('Equipment created');
      setCreateVisible(false);
      createForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  const handleLog = async (values: any) => {
    try {
      await api.logEquipment(selectedEq?.id, values);
      message.success('Equipment logged, journal posted');
      setLogVisible(false);
      logForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 15 }}>Equipment</Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}
            style={{ background: '#6366f1' }}>New Equipment</Button>
        </Space>
      </div>

      <Table dataSource={data} rowKey="id" loading={loading} size="small"
        columns={[
          { title: 'Code', dataIndex: 'code', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Name', dataIndex: 'name' },
          { title: 'Type', dataIndex: 'type', width: 120 },
          { title: 'Status', dataIndex: 'status', width: 100,
            render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
          { title: 'Rate/hr', dataIndex: 'hourly_rate', width: 100,
            render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
          { title: 'Total Hours', dataIndex: 'total_hours', width: 90 },
          { title: 'Total Fuel', dataIndex: 'total_fuel', width: 100,
            render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
          { title: '', key: 'actions', width: 80,
            render: (_: any, r: any) => (
              <Button size="small" onClick={() => { setSelectedEq(r); setLogVisible(true); }}>
                Log Usage
              </Button>
            )},
        ]}
        locale={{ emptyText: <Empty description="No equipment" /> }}
      />

      {/* Create Modal */}
      <Modal title="New Equipment" open={createVisible}
        onCancel={() => setCreateVisible(false)} footer={null}>
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="code" label="Code" rules={[{ required: true }]}><Input placeholder="EQ-002" /></Form.Item></Col>
            <Col span={16}><Form.Item name="name" label="Name" rules={[{ required: true }]}><Input placeholder="e.g. Tower Crane" /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="type" label="Type"><Input placeholder="Crane, Excavator, etc." /></Form.Item></Col>
            <Col span={12}><Form.Item name="hourly_rate" label="Hourly Rate (SAR)"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Create</Button>
        </Form>
      </Modal>

      {/* Log Usage Modal */}
      <Modal title={`Log Usage — ${selectedEq?.name || ''}`} open={logVisible}
        onCancel={() => setLogVisible(false)} footer={null}>
        <Form form={logForm} layout="vertical" onFinish={handleLog}>
          <Form.Item name="hours" label="Hours" rules={[{ required: true }]}>
            <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="fuel_cost" label="Fuel Cost (SAR)">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" style={{ background: '#f59e0b' }}>
            Log & Post Journal
          </Button>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Site Operations — Diary, RFI, Inspections
   ═══════════════════════════════════════════════════ */

const SiteOpsTab: React.FC = () => {
  const [diaries, setDiaries] = useState<any[]>([]);
  const [rfis, setRfis] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [diaryVisible, setDiaryVisible] = useState(false);
  const [rfiVisible, setRfiVisible] = useState(false);
  const [diaryForm] = Form.useForm();
  const [rfiForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [d, r, p]: any[] = await Promise.all([api.diaryList(), api.rfiList(), api.projects()]);
      setDiaries(d.data || []);
      setRfis(r.data || []);
      setProjects(p.data || []);
    } catch { }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDiary = async (values: any) => {
    try {
      await api.createDiary(values);
      message.success('Site diary created');
      setDiaryVisible(false);
      diaryForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  const handleRFI = async (values: any) => {
    try {
      await api.createRFI(values);
      message.success('RFI created');
      setRfiVisible(false);
      rfiForm.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  return (
    <div>
      <Tabs items={[
        {
          key: 'diary',
          label: <Space><FileTextOutlined />Site Diary <Badge count={diaries.length} size="small" /></Space>,
          children: (
            <>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setDiaryVisible(true)}
                  style={{ background: '#6366f1' }}>New Entry</Button>
              </div>
              <Table dataSource={diaries} rowKey="id" loading={loading} size="small"
                columns={[
                  { title: 'Date', dataIndex: 'diary_date', width: 110,
                    render: (v: string) => v ? new Date(v).toLocaleDateString('en-GB') : '—' },
                  { title: 'Weather', dataIndex: 'weather', width: 90 },
                  { title: 'Manpower', dataIndex: 'manpower_count', width: 80 },
                  { title: 'Progress', dataIndex: 'work_progress' },
                  { title: 'Notes', dataIndex: 'notes' },
                ]}
                locale={{ emptyText: <Empty description="No diary entries" /> }}
              />
            </>
          ),
        },
        {
          key: 'rfi',
          label: <Space><AuditOutlined />RFIs <Badge count={rfis.length} size="small" /></Space>,
          children: (
            <>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setRfiVisible(true)}
                  style={{ background: '#6366f1' }}>New RFI</Button>
              </div>
              <Table dataSource={rfis} rowKey="id" loading={loading} size="small"
                columns={[
                  { title: 'Number', dataIndex: 'rfi_number', render: (v: string) => <Text code>{v}</Text> },
                  { title: 'Subject', dataIndex: 'subject' },
                  { title: 'Status', dataIndex: 'status', width: 100,
                    render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
                  { title: 'Sent', dataIndex: 'sent_date', width: 110,
                    render: (v: string) => v ? new Date(v).toLocaleDateString('en-GB') : '—' },
                ]}
                locale={{ emptyText: <Empty description="No RFIs" /> }}
              />
            </>
          ),
        },
      ]} />

      {/* Diary Modal */}
      <Modal title="New Site Diary" open={diaryVisible}
        onCancel={() => setDiaryVisible(false)} footer={null}>
        <Form form={diaryForm} layout="vertical" onFinish={handleDiary}>
          <Form.Item name="project_id" label="Project" rules={[{ required: true }]}>
            <Select placeholder="Select project" showSearch optionFilterProp="label">
              {projects.map(p => <Select.Option key={p.id} value={p.id} label={p.name}>{p.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="diary_date" label="Date" rules={[{ required: true }]}><Input type="date" /></Form.Item></Col>
            <Col span={12}><Form.Item name="weather" label="Weather"><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="manpower_count" label="Manpower Count">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="work_progress" label="Work Progress">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Create</Button>
        </Form>
      </Modal>

      {/* RFI Modal */}
      <Modal title="New RFI" open={rfiVisible}
        onCancel={() => setRfiVisible(false)} footer={null}>
        <Form form={rfiForm} layout="vertical" onFinish={handleRFI}>
          <Form.Item name="project_id" label="Project" rules={[{ required: true }]}>
            <Select placeholder="Select project" showSearch optionFilterProp="label">
              {projects.map(p => <Select.Option key={p.id} value={p.id} label={p.name}>{p.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="subject" label="Subject" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Create RFI</Button>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Subcontractors
   ═══════════════════════════════════════════════════ */

const SubcontractorsTab: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { const r: any = await api.subcontractors(); setData(r.data || []); } catch { }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (values: any) => {
    try {
      await api.createSubcontractor(values);
      message.success('Subcontractor created');
      setVisible(false);
      form.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'Failed');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 15 }}>Subcontractors</Text>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setVisible(true)}
            style={{ background: '#6366f1' }}>New Subcontractor</Button>
        </Space>
      </div>
      <Table dataSource={data} rowKey="id" loading={loading} size="small"
        columns={[
          { title: 'Name', dataIndex: 'name' },
          { title: 'Trade', dataIndex: 'trade' },
          { title: 'Contact', dataIndex: 'contact_person' },
          { title: 'Phone', dataIndex: 'phone' },
          { title: 'Email', dataIndex: 'email' },
          { title: 'Contracts', dataIndex: 'total_contracts', width: 100,
            render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
          { title: 'Paid', dataIndex: 'total_paid', width: 100,
            render: (v: number) => `${(v || 0).toLocaleString()} SAR` },
        ]}
        locale={{ emptyText: <Empty description="No subcontractors" /> }}
      />
      <Modal title="New Subcontractor" open={visible} onCancel={() => setVisible(false)} footer={null}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="Company Name" rules={[{ required: true }]}>
            <Input placeholder="ABC Contracting" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="trade" label="Trade"><Input placeholder="Electrical, Plumbing..." /></Form.Item></Col>
            <Col span={12}><Form.Item name="contact_person" label="Contact Person"><Input /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="phone" label="Phone"><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="email" label="Email"><Input /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" style={{ background: '#6366f1' }}>Create</Button>
        </Form>
      </Modal>
    </div>
  );
};

/* ═══════════════════════════════════════════════════
   Main Construction Workspace
   ═══════════════════════════════════════════════════ */

const ConstructionPage: React.FC = () => (
  <div style={{ maxWidth: 1400, margin: '0 auto' }}>
    <Tabs
      defaultActiveKey="dashboard"
      style={{ padding: '0 0 24px' }}
      items={[
        { key: 'dashboard', label: <Space><DashboardOutlined />Dashboard</Space>, children: <DashboardTab /> },
        { key: 'projects', label: <Space><ProjectOutlined />Projects</Space>, children: <ProjectsTab /> },
        { key: 'procurement', label: <Space><ShoppingCartOutlined />Procurement</Space>, children: <ProcurementTab /> },
        { key: 'stock', label: <Space><ShopOutlined />Stock</Space>, children: <StockTab /> },
        { key: 'equipment', label: <Space><ToolOutlined />Equipment</Space>, children: <EquipmentTab /> },
        { key: 'site', label: <Space><EnvironmentOutlined />Site Operations</Space>, children: <SiteOpsTab /> },
        { key: 'subcontractors', label: <Space><TeamOutlined />Subcontractors</Space>, children: <SubcontractorsTab /> },
      ]}
    />
  </div>
);

export default ConstructionPage;
