/**
 * EOS System — Sales & CRM Page
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tabs,
  Row,
  Col,
  Statistic,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  message,
  Popconfirm,
  Typography,
  Avatar,
  Progress,
  Descriptions,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  TeamOutlined,
  UserOutlined,
  ShopOutlined,
  DollarOutlined,
  PhoneOutlined,
  MailOutlined,
} from '@ant-design/icons';
import { salesApi } from '../services';
import type { Customer, Lead, Opportunity, Quote } from '../types';

const { TabPane } = Tabs;
const { Title } = Typography;

const SalesPage: React.FC = () => {
  // =====================================================
  // State
  // =====================================================
  const [activeTab, setActiveTab] = useState('customers');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalCustomers, setTotalCustomers] = useState(0);
  const [totalLeads, setTotalLeads] = useState(0);
  const [totalOpportunities, setTotalOpportunities] = useState(0);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  
  // Modals
  const [customerModalVisible, setCustomerModalVisible] = useState(false);
  const [leadModalVisible, setLeadModalVisible] = useState(false);
  const [opportunityModalVisible, setOpportunityModalVisible] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  
  // Forms
  const [customerForm] = Form.useForm();
  const [leadForm] = Form.useForm();
  const [opportunityForm] = Form.useForm();

  // =====================================================
  // Fetch Data
  // =====================================================

  const fetchCustomers = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await salesApi.listCustomers({ page, page_size: pageSize });
      setCustomers(result.data);
      setTotalCustomers(result.total);
    } catch (error) {
      message.error('خطأ في تحميل العملاء');
    } finally {
      setLoading(false);
    }
  };

  const fetchLeads = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await salesApi.listLeads({ page, page_size: pageSize });
      setLeads(result.data);
      setTotalLeads(result.total);
    } catch (error) {
      message.error('خطأ في تحميل العملاء المحتملين');
    } finally {
      setLoading(false);
    }
  };

  const fetchOpportunities = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await salesApi.listOpportunities({ page, page_size: pageSize });
      setOpportunities(result.data);
      setTotalOpportunities(result.total);
    } catch (error) {
      message.error('خطأ في تحميل الفرص');
    } finally {
      setLoading(false);
    }
  };

  const fetchQuotes = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await salesApi.listQuotes({ page, page_size: pageSize });
      setQuotes(result.data);
    } catch (error) {
      message.error('خطأ في تحميل عروض الأسعار');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
    fetchLeads();
    fetchOpportunities();
    fetchQuotes();
  }, []);

  // =====================================================
  // Customer Handlers
  // =====================================================

  const handleCreateCustomer = () => {
    setEditingCustomer(null);
    customerForm.resetFields();
    setCustomerModalVisible(true);
  };

  const handleEditCustomer = (customer: Customer) => {
    setEditingCustomer(customer);
    customerForm.setFieldsValue(customer);
    setCustomerModalVisible(true);
  };

  const handleViewCustomer = (customer: Customer) => {
    setSelectedCustomer(customer);
  };

  const handleSaveCustomer = async () => {
    try {
      const values = await customerForm.validateFields();
      
      if (editingCustomer) {
        await salesApi.updateCustomer(editingCustomer.id, values);
        message.success('تم تحديث بيانات العميل بنجاح');
      } else {
        await salesApi.createCustomer(values);
        message.success('تم إضافة العميل بنجاح');
      }
      
      setCustomerModalVisible(false);
      fetchCustomers();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ بيانات العميل');
    }
  };

  const handleDeleteCustomer = async (id: string) => {
    try {
      await salesApi.deleteCustomer(id);
      message.success('تم حذف العميل بنجاح');
      fetchCustomers();
    } catch (error) {
      message.error('حدث خطأ أثناء حذف العميل');
    }
  };

  // =====================================================
  // Lead Handlers
  // =====================================================

  const handleCreateLead = () => {
    leadForm.resetFields();
    setLeadModalVisible(true);
  };

  const handleSaveLead = async () => {
    try {
      const values = await leadForm.validateFields();
      await salesApi.createLead(values);
      message.success('تم إضافة العميل المحتمل بنجاح');
      setLeadModalVisible(false);
      fetchLeads();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ البيانات');
    }
  };

  const handleConvertLead = async (id: string) => {
    try {
      await salesApi.convertLead(id);
      message.success('تم تحويل العميل المحتمل إلى فرصة');
      fetchLeads();
      fetchOpportunities();
    } catch (error) {
      message.error('حدث خطأ أثناء التحويل');
    }
  };

  // =====================================================
  // Opportunity Handlers
  // =====================================================

  const handleCreateOpportunity = () => {
    opportunityForm.resetFields();
    setOpportunityModalVisible(true);
  };

  const handleSaveOpportunity = async () => {
    try {
      const values = await opportunityForm.validateFields();
      await salesApi.createOpportunity(values);
      message.success('تم إضافة الفرصة بنجاح');
      setOpportunityModalVisible(false);
      fetchOpportunities();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ البيانات');
    }
  };

  // =====================================================
  // Table Columns
  // =====================================================

  const customerColumns = [
    {
      title: 'العميل',
      key: 'customer',
      render: (_: any, record: Customer) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 'bold' }}>{record.name}</div>
            {record.name_ar && (
              <div style={{ color: '#8c8c8c', fontSize: 12 }}>{record.name_ar}</div>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: 'النوع',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'company' ? 'blue' : 'green'}>
          {type === 'company' ? 'شركة' : 'فرد'}
        </Tag>
      ),
    },
    {
      title: 'البريد الإلكتروني',
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => email ? (
        <Space>
          <MailOutlined /> {email}
        </Space>
      ) : '---',
    },
    {
      title: 'الهاتف',
      dataIndex: 'phone',
      key: 'phone',
      render: (phone: string) => phone ? (
        <Space>
          <PhoneOutlined /> {phone}
        </Space>
      ) : '---',
    },
    {
      title: 'إجمالي المشتريات',
      dataIndex: 'total_spent',
      key: 'total_spent',
      render: (spent: number) => (
        <span style={{ fontWeight: 'bold' }}>
          {spent.toLocaleString('ar-EG')} ج.م
        </span>
      ),
    },
    {
      title: 'إجراءات',
      key: 'actions',
      render: (_: any, record: Customer) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewCustomer(record)}
          />
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditCustomer(record)}
          />
          <Popconfirm
            title="هل أنت متأكد من حذف هذا العميل؟"
            onConfirm={() => handleDeleteCustomer(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const leadColumns = [
    {
      title: 'العميل المحتمل',
      key: 'lead',
      render: (_: any, record: Lead) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{record.first_name} {record.last_name}</div>
          {record.company_name && (
            <div style={{ color: '#8c8c8c', fontSize: 12 }}>{record.company_name}</div>
          )}
        </div>
      ),
    },
    {
      title: 'المصدر',
      dataIndex: 'source',
      key: 'source',
      render: (source: string) => source ? <Tag>{source}</Tag> : '---',
    },
    {
      title: 'الحالة',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          new: { color: 'blue', text: 'جديد' },
          contacted: { color: 'orange', text: 'تم التواصل' },
          qualified: { color: 'green', text: 'مؤهل' },
          unqualified: { color: 'red', text: 'غير مؤهل' },
        };
        const { color, text } = statusMap[status] || { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: 'التقييم',
      dataIndex: 'score',
      key: 'score',
      render: (score: number) => (
        <Progress percent={score} size="small" />
      ),
    },
    {
      title: 'إجراءات',
      key: 'actions',
      render: (_: any, record: Lead) => (
        <Space>
          {record.status !== 'unqualified' && (
            <Button
              type="link"
              onClick={() => handleConvertLead(record.id)}
            >
              تحويل إلى فرصة
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const opportunityColumns = [
    {
      title: 'الفرصة',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <span style={{ fontWeight: 'bold' }}>{name}</span>
      ),
    },
    {
      title: 'المرحلة',
      dataIndex: 'stage',
      key: 'stage',
      render: (stage: string) => {
        const stageMap: Record<string, { color: string; text: string }> = {
          qualification: { color: 'blue', text: 'أولية' },
          needs_analysis: { color: 'cyan', text: 'تحليل الاحتياجات' },
          proposal: { color: 'orange', text: 'عرض سعر' },
          negotiation: { color: 'purple', text: 'تفاوض' },
          closed_won: { color: 'green', text: 'فاز' },
          closed_lost: { color: 'red', text: 'خسر' },
        };
        const { color, text } = stageMap[stage] || { color: 'default', text: stage };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: 'المبلغ',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => (
        <span style={{ fontWeight: 'bold' }}>
          {amount.toLocaleString('ar-EG')} ج.م
        </span>
      ),
    },
    {
      title: 'احتمال الإغلاق',
      dataIndex: 'probability',
      key: 'probability',
      render: (prob: number) => prob ? (
        <Progress percent={prob} size="small" />
      ) : '---',
    },
    {
      title: 'تاريخ الإغلاق المتوقع',
      dataIndex: 'expected_close_date',
      key: 'expected_close_date',
      render: (date: string) => date || '---',
    },
  ];

  // =====================================================
  // Render
  // =====================================================

  return (
    <div>
      <Title level={4}>
        <ShopOutlined /> المبيعات وCRM
      </Title>

      {/* Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="العملاء"
              value={totalCustomers}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="العملاء المحتملون"
              value={totalLeads}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="الفرص النشطة"
              value={totalOpportunities}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="قيمة Pipeline"
              value={opportunities.reduce((sum, opp) => sum + opp.amount, 0)}
              prefix={<DollarOutlined />}
              suffix="ج.م"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="العملاء" key="customers">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateCustomer}>
                  إضافة عميل
                </Button>
                <Input.Search placeholder="بحث في العملاء" style={{ width: 300 }} />
              </Space>
            </div>
            <Table
              columns={customerColumns}
              dataSource={customers}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalCustomers,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} عميل`,
              }}
            />
          </TabPane>

          <TabPane 
            tab={
              <Badge count={leads.filter(l => l.status === 'new').length}>
                العملاء المحتملون
              </Badge>
            } 
            key="leads"
          >
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateLead}>
                إضافة عميل محتمل
              </Button>
            </div>
            <Table
              columns={leadColumns}
              dataSource={leads}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalLeads,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} عميل محتمل`,
              }}
            />
          </TabPane>

          <TabPane tab="الفرص" key="opportunities">
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateOpportunity}>
                إضافة فرصة
              </Button>
            </div>
            <Table
              columns={opportunityColumns}
              dataSource={opportunities}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalOpportunities,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} فرصة`,
              }}
            />
          </TabPane>

          <TabPane tab="عروض الأسعار" key="quotes">
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />}>
                إنشاء عرض سعر
              </Button>
            </div>
            <Table
              dataSource={quotes}
              rowKey="id"
              columns={[
                {
                  title: 'رقم العرض',
                  dataIndex: 'quote_number',
                  key: 'quote_number',
                },
                {
                  title: 'العميل',
                  dataIndex: 'customer_id',
                  key: 'customer_id',
                },
                {
                  title: 'المبلغ',
                  dataIndex: 'total_amount',
                  key: 'total_amount',
                  render: (amount: number) => (
                    <span style={{ fontWeight: 'bold' }}>
                      {amount.toLocaleString('ar-EG')} ج.م
                    </span>
                  ),
                },
                {
                  title: 'الحالة',
                  dataIndex: 'status',
                  key: 'status',
                  render: (status: string) => {
                    const statusMap: Record<string, { color: string; text: string }> = {
                      draft: { color: 'default', text: 'مسودة' },
                      sent: { color: 'blue', text: 'مرسل' },
                      accepted: { color: 'green', text: 'مقبول' },
                      rejected: { color: 'red', text: 'مرفوض' },
                      expired: { color: 'orange', text: 'منتهي' },
                    };
                    const { color, text } = statusMap[status] || { color: 'default', text: status };
                    return <Tag color={color}>{text}</Tag>;
                  },
                },
                {
                  title: 'صالح حتى',
                  dataIndex: 'valid_until',
                  key: 'valid_until',
                },
              ]}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Customer Modal */}
      <Modal
        title={editingCustomer ? 'تعديل بيانات العميل' : 'إضافة عميل جديد'}
        open={customerModalVisible}
        onOk={handleSaveCustomer}
        onCancel={() => setCustomerModalVisible(false)}
        width={600}
      >
        <Form form={customerForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="اسم العميل"
                rules={[{ required: true, message: 'أدخل اسم العميل' }]}
              >
                <Input placeholder="اسم العميل" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="name_ar" label="اسم العميل (عربي)">
                <Input placeholder="اسم العميل بالعربي" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="type"
                label="نوع العميل"
                rules={[{ required: true, message: 'اختر نوع العميل' }]}
              >
                <Select placeholder="اختر النوع">
                  <Select.Option value="individual">فرد</Select.Option>
                  <Select.Option value="company">شركة</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="tax_id" label="الرقم الضريبي">
                <Input placeholder="الرقم الضريبي" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="email" label="البريد الإلكتروني">
                <Input placeholder="email@example.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="رقم الهاتف">
                <Input placeholder="+201234567890" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="address" label="العنوان">
            <Input.TextArea rows={2} placeholder="عنوان العميل" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Lead Modal */}
      <Modal
        title="إضافة عميل محتمل"
        open={leadModalVisible}
        onOk={handleSaveLead}
        onCancel={() => setLeadModalVisible(false)}
        width={600}
      >
        <Form form={leadForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="first_name"
                label="الاسم الأول"
                rules={[{ required: true, message: 'أدخل الاسم الأول' }]}
              >
                <Input placeholder="الاسم الأول" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="last_name"
                label="اسم العائلة"
                rules={[{ required: true, message: 'أدخل اسم العائلة' }]}
              >
                <Input placeholder="اسم العائلة" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="company_name" label="اسم الشركة">
                <Input placeholder="اسم الشركة" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="source" label="المصدر">
                <Select placeholder="اختر المصدر" allowClear>
                  <Select.Option value="website">الموقع الإلكتروني</Select.Option>
                  <Select.Option value="referral">إحالة</Select.Option>
                  <Select.Option value="cold_call">اتصال بارد</Select.Option>
                  <Select.Option value="social_media">وسائل التواصل</Select.Option>
                  <Select.Option value="other">أخرى</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="email" label="البريد الإلكتروني">
                <Input placeholder="email@example.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="رقم الهاتف">
                <Input placeholder="+201234567890" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="ملاحظات">
            <Input.TextArea rows={3} placeholder="ملاحظات حول العميل المحتمل" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Opportunity Modal */}
      <Modal
        title="إضافة فرصة جديدة"
        open={opportunityModalVisible}
        onOk={handleSaveOpportunity}
        onCancel={() => setOpportunityModalVisible(false)}
        width={600}
      >
        <Form form={opportunityForm} layout="vertical">
          <Form.Item
            name="name"
            label="اسم الفرصة"
            rules={[{ required: true, message: 'أدخل اسم الفرصة' }]}
          >
            <Input placeholder="اسم الفرصة" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="amount"
                label="المبلغ"
                rules={[{ required: true, message: 'أدخل المبلغ' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  placeholder="0"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="stage" label="المرحلة">
                <Select placeholder="اختر المرحلة">
                  <Select.Option value="qualification">أولية</Select.Option>
                  <Select.Option value="needs_analysis">تحليل الاحتياجات</Select.Option>
                  <Select.Option value="proposal">عرض سعر</Select.Option>
                  <Select.Option value="negotiation">تفاوض</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="expected_close_date" label="تاريخ الإغلاق المتوقع">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="probability" label="احتمال الإغلاق (%)">
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="customer_id" label="العميل">
            <Select placeholder="اختر العميل" allowClear showSearch>
              {customers.map((customer) => (
                <Select.Option key={customer.id} value={customer.id}>
                  {customer.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="notes" label="ملاحظات">
            <Input.TextArea rows={3} placeholder="ملاحظات حول الفرصة" />
          </Form.Item>
        </Form>
      </Modal>

      {/* View Customer Modal */}
      <Modal
        title={`بيانات العميل: ${selectedCustomer?.name}`}
        open={!!selectedCustomer}
        onCancel={() => setSelectedCustomer(null)}
        footer={null}
        width={700}
      >
        {selectedCustomer && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="اسم العميل">{selectedCustomer.name}</Descriptions.Item>
            <Descriptions.Item label="الاسم (عربي)">{selectedCustomer.name_ar || '---'}</Descriptions.Item>
            <Descriptions.Item label="النوع">
              <Tag color={selectedCustomer.type === 'company' ? 'blue' : 'green'}>
                {selectedCustomer.type === 'company' ? 'شركة' : 'فرد'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="الرقم الضريبي">{selectedCustomer.tax_id || '---'}</Descriptions.Item>
            <Descriptions.Item label="البريد الإلكتروني">{selectedCustomer.email || '---'}</Descriptions.Item>
            <Descriptions.Item label="الهاتف">{selectedCustomer.phone || '---'}</Descriptions.Item>
            <Descriptions.Item label="العنوان" span={2}>{selectedCustomer.address || '---'}</Descriptions.Item>
            <Descriptions.Item label="إجمالي الطلبات">{selectedCustomer.total_orders}</Descriptions.Item>
            <Descriptions.Item label="إجمالي المشتريات">{selectedCustomer.total_spent.toLocaleString('ar-EG')} ج.م</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default SalesPage;
