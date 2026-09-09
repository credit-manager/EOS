/**
 * EOS System — Accounting Page
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
  DatePicker,
  InputNumber,
  message,
  Popconfirm,
  Typography,
  Dropdown,
  Menu,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  DollarOutlined,
  BankOutlined,
  BookOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  PrinterOutlined,
  DownloadOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import { accountingApi } from '../services';
import type { Account, JournalEntry, JournalEntryCreate } from '../types';

const { TabPane } = Tabs;
const { Title } = Typography;
const { RangePicker } = DatePicker;

const AccountingPage: React.FC = () => {
  // =====================================================
  // State
  // =====================================================
  const [activeTab, setActiveTab] = useState('accounts');
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalAccounts, setTotalAccounts] = useState(0);
  const [totalEntries, setTotalEntries] = useState(0);
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);
  
  // Modals
  const [accountModalVisible, setAccountModalVisible] = useState(false);
  const [entryModalVisible, setEntryModalVisible] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [editingEntry, setEditingEntry] = useState<JournalEntry | null>(null);
  
  // Forms
  const [accountForm] = Form.useForm();
  const [entryForm] = Form.useForm();
  const [entryLines, setEntryLines] = useState<any[]>([
    { account_id: '', debit: 0, credit: 0 },
    { account_id: '', debit: 0, credit: 0 },
  ]);

  // =====================================================
  // Fetch Data
  // =====================================================

  const fetchAccounts = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await accountingApi.listAccounts({ page, page_size: pageSize });
      setAccounts(result.data);
      setTotalAccounts(result.total);
    } catch (error) {
      message.error('خطأ في تحميل الحسابات');
    } finally {
      setLoading(false);
    }
  };

  const fetchJournalEntries = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await accountingApi.listJournalEntries({ page, page_size: pageSize });
      setJournalEntries(result.data);
      setTotalEntries(result.total);
    } catch (error) {
      message.error('خطأ في تحميل القيود');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
    fetchJournalEntries();
  }, []);

  // =====================================================
  // Account Handlers
  // =====================================================

  const handleCreateAccount = () => {
    setEditingAccount(null);
    accountForm.resetFields();
    setAccountModalVisible(true);
  };

  const handleEditAccount = (account: Account) => {
    setEditingAccount(account);
    accountForm.setFieldsValue(account);
    setAccountModalVisible(true);
  };

  const handleSaveAccount = async () => {
    try {
      const values = await accountForm.validateFields();
      
      if (editingAccount) {
        await accountingApi.updateAccount(editingAccount.id, values);
        message.success('تم تحديث الحساب بنجاح');
      } else {
        await accountingApi.createAccount(values);
        message.success('تم إنشاء الحساب بنجاح');
      }
      
      setAccountModalVisible(false);
      fetchAccounts();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ الحساب');
    }
  };

  const handleDeleteAccount = async (id: string) => {
    try {
      await accountingApi.deleteAccount(id);
      message.success('تم حذف الحساب بنجاح');
      fetchAccounts();
    } catch (error) {
      message.error('حدث خطأ أثناء حذف الحساب');
    }
  };

  // =====================================================
  // Journal Entry Handlers
  // =====================================================

  const handleCreateEntry = () => {
    setEditingEntry(null);
    entryForm.resetFields();
    setEntryLines([
      { account_id: '', debit: 0, credit: 0 },
      { account_id: '', debit: 0, credit: 0 },
    ]);
    setEntryModalVisible(true);
  };

  const handleViewEntry = (entry: JournalEntry) => {
    setSelectedEntry(entry);
  };

  const handleSaveEntry = async () => {
    try {
      const values = await entryForm.validateFields();
      
      // Validate lines
      const totalDebit = entryLines.reduce((sum, line) => sum + (line.debit || 0), 0);
      const totalCredit = entryLines.reduce((sum, line) => sum + (line.credit || 0), 0);
      
      if (Math.abs(totalDebit - totalCredit) > 0.01) {
        message.error('المدين يجب أن يساوي الدائن');
        return;
      }
      
      if (totalDebit === 0) {
        message.error('يجب إدخال مبلغ أكبر من صفر');
        return;
      }
      
      const entryData: JournalEntryCreate = {
        ...values,
        lines: entryLines.filter(line => line.account_id && (line.debit > 0 || line.credit > 0)),
      };
      
      await accountingApi.createJournalEntry(entryData);
      message.success('تم إنشاء القيد بنجاح');
      
      setEntryModalVisible(false);
      fetchJournalEntries();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ القيد');
    }
  };

  const handlePostEntry = async (id: string) => {
    try {
      await accountingApi.postJournalEntry(id);
      message.success('تم ترحيل القيد بنجاح');
      fetchJournalEntries();
    } catch (error) {
      message.error('حدث خطأ أثناء ترحيل القيد');
    }
  };

  const addEntryLine = () => {
    setEntryLines([...entryLines, { account_id: '', debit: 0, credit: 0 }]);
  };

  const removeEntryLine = (index: number) => {
    if (entryLines.length > 2) {
      setEntryLines(entryLines.filter((_, i) => i !== index));
    }
  };

  const updateEntryLine = (index: number, field: string, value: any) => {
    const newLines = [...entryLines];
    newLines[index] = { ...newLines[index], [field]: value };
    setEntryLines(newLines);
  };

  // =====================================================
  // Table Columns
  // =====================================================

  const accountColumns = [
    {
      title: 'الكود',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: 'اسم الحساب',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'اسم الحساب (عربي)',
      dataIndex: 'name_ar',
      key: 'name_ar',
    },
    {
      title: 'النوع',
      dataIndex: 'account_type',
      key: 'account_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          asset: { color: 'blue', text: 'أصول' },
          liability: { color: 'red', text: 'التزامات' },
          equity: { color: 'green', text: 'حقوق ملكية' },
          revenue: { color: 'cyan', text: 'إيرادات' },
          expense: { color: 'orange', text: 'مصروفات' },
        };
        const { color, text } = typeMap[type] || { color: 'default', text: type };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: 'الرصيد',
      dataIndex: 'balance',
      key: 'balance',
      render: (balance: number) => (
        <span style={{ fontWeight: 'bold' }}>
          {balance.toLocaleString('ar-EG')} ج.م
        </span>
      ),
    },
    {
      title: 'الحالة',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? 'نشط' : 'غير نشط'}
        </Tag>
      ),
    },
    {
      title: 'إجراءات',
      key: 'actions',
      render: (_: any, record: Account) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleEditAccount(record)}
          />
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditAccount(record)}
          />
          <Popconfirm
            title="هل أنت متأكد من حذف هذا الحساب؟"
            onConfirm={() => handleDeleteAccount(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const journalColumns = [
    {
      title: 'رقم القيد',
      dataIndex: 'entry_number',
      key: 'entry_number',
      width: 150,
    },
    {
      title: 'التاريخ',
      dataIndex: 'entry_date',
      key: 'entry_date',
      width: 120,
    },
    {
      title: 'الوصف',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'المدين',
      dataIndex: 'total_debit',
      key: 'total_debit',
      render: (amount: number) => (
        <span style={{ color: '#52c41a' }}>
          {amount.toLocaleString('ar-EG')} ج.م
        </span>
      ),
    },
    {
      title: 'الدائن',
      dataIndex: 'total_credit',
      key: 'total_credit',
      render: (amount: number) => (
        <span style={{ color: '#ff4d4f' }}>
          {amount.toLocaleString('ar-EG')} ج.م
        </span>
      ),
    },
    {
      title: 'الحالة',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
          draft: { color: 'orange', icon: <ClockCircleOutlined />, text: 'مسودة' },
          posted: { color: 'green', icon: <CheckCircleOutlined />, text: 'مرحل' },
          reversed: { color: 'red', icon: <CloseCircleOutlined />, text: 'معكوس' },
        };
        const { color, icon, text } = statusMap[status] || { color: 'default', icon: null, text: status };
        return <Tag color={color} icon={icon}>{text}</Tag>;
      },
    },
    {
      title: 'إجراءات',
      key: 'actions',
      render: (_: any, record: JournalEntry) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewEntry(record)}
          />
          {record.status === 'draft' && (
            <Button
              type="link"
              icon={<CheckCircleOutlined />}
              onClick={() => handlePostEntry(record.id)}
            >
              ترحيل
            </Button>
          )}
          <Dropdown
            overlay={
              <Menu>
                <Menu.Item key="print" icon={<PrinterOutlined />}>
                  طباعة
                </Menu.Item>
                <Menu.Item key="download" icon={<DownloadOutlined />}>
                  تصدير
                </Menu.Item>
              </Menu>
            }
          >
            <Button type="link" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // =====================================================
  // Render
  // =====================================================

  return (
    <div>
      <Title level={4}>
        <BookOutlined /> المحاسبة والمالية
      </Title>

      {/* Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="إجمالي الحسابات"
              value={totalAccounts}
              prefix={<BankOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="القيود المحاسبية"
              value={totalEntries}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="إجمالي الأصول"
              value={0}
              prefix={<DollarOutlined />}
              suffix="ج.م"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="صافي الربح"
              value={0}
              prefix={<DollarOutlined />}
              suffix="ج.م"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="دليل الحسابات" key="accounts">
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateAccount}>
                إضافة حساب
              </Button>
            </div>
            <Table
              columns={accountColumns}
              dataSource={accounts}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalAccounts,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} حساب`,
              }}
              onChange={(pagination) => fetchAccounts(pagination.current, pagination.pageSize)}
            />
          </TabPane>

          <TabPane tab="القيود اليومية" key="journal">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateEntry}>
                  إنشاء قيد جديد
                </Button>
                <RangePicker />
              </Space>
            </div>
            <Table
              columns={journalColumns}
              dataSource={journalEntries}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalEntries,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} قيد`,
              }}
              onChange={(pagination) => fetchJournalEntries(pagination.current, pagination.pageSize)}
            />
          </TabPane>

          <TabPane tab="التقارير" key="reports">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} lg={8}>
                <Card hoverable>
                  <Statistic title="ميزان المراجعة" value="---" />
                  <Button type="link" style={{ marginTop: 16 }}>
                    عرض التقرير
                  </Button>
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={8}>
                <Card hoverable>
                  <Statistic title="قائمة الدخل" value="---" />
                  <Button type="link" style={{ marginTop: 16 }}>
                    عرض التقرير
                  </Button>
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={8}>
                <Card hoverable>
                  <Statistic title="الميزانية العمومية" value="---" />
                  <Button type="link" style={{ marginTop: 16 }}>
                    عرض التقرير
                  </Button>
                </Card>
              </Col>
            </Row>
          </TabPane>
        </Tabs>
      </Card>

      {/* Account Modal */}
      <Modal
        title={editingAccount ? 'تعديل الحساب' : 'إضافة حساب جديد'}
        open={accountModalVisible}
        onOk={handleSaveAccount}
        onCancel={() => setAccountModalVisible(false)}
        width={600}
      >
        <Form form={accountForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="code"
                label="كود الحساب"
                rules={[{ required: true, message: 'أدخل كود الحساب' }]}
              >
                <Input placeholder="مثال: 1001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="account_type"
                label="نوع الحساب"
                rules={[{ required: true, message: 'اختر نوع الحساب' }]}
              >
                <Select placeholder="اختر النوع">
                  <Select.Option value="asset">أصول</Select.Option>
                  <Select.Option value="liability">التزامات</Select.Option>
                  <Select.Option value="equity">حقوق ملكية</Select.Option>
                  <Select.Option value="revenue">إيرادات</Select.Option>
                  <Select.Option value="expense">مصروفات</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="اسم الحساب (إنجليزي)"
                rules={[{ required: true, message: 'أدخل اسم الحساب' }]}
              >
                <Input placeholder="Account Name" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="name_ar"
                label="اسم الحساب (عربي)"
                rules={[{ required: true, message: 'أدخل اسم الحساب بالعربي' }]}
              >
                <Input placeholder="اسم الحساب" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="parent_id" label="الحساب الأب">
            <Select placeholder="اختر الحساب الأب" allowClear>
              {accounts.map((acc) => (
                <Select.Option key={acc.id} value={acc.id}>
                  {acc.code} - {acc.name_ar}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Journal Entry Modal */}
      <Modal
        title={editingEntry ? 'تعديل القيد' : 'إنشاء قيد محاسبي جديد'}
        open={entryModalVisible}
        onOk={handleSaveEntry}
        onCancel={() => setEntryModalVisible(false)}
        width={900}
      >
        <Form form={entryForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="entry_date"
                label="التاريخ"
                rules={[{ required: true, message: 'اختر التاريخ' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="reference" label="المرجع">
                <Input placeholder="رقم المرجع" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="description"
            label="الوصف"
            rules={[{ required: true, message: 'أدخل الوصف' }]}
          >
            <Input.TextArea rows={2} placeholder="وصف القيد" />
          </Form.Item>
        </Form>

        {/* Entry Lines */}
        <Card title="بنود القيد" size="small">
          <Table
            dataSource={entryLines}
            rowKey={(_, index) => index?.toString() || '0'}
            pagination={false}
            columns={[
              {
                title: 'الحساب',
                dataIndex: 'account_id',
                render: (_: any, __: any, index: number) => (
                  <Select
                    style={{ width: '100%' }}
                    placeholder="اختر الحساب"
                    value={entryLines[index].account_id}
                    onChange={(value) => updateEntryLine(index, 'account_id', value)}
                  >
                    {accounts.map((acc) => (
                      <Select.Option key={acc.id} value={acc.id}>
                        {acc.code} - {acc.name_ar}
                      </Select.Option>
                    ))}
                  </Select>
                ),
              },
              {
                title: 'المدين',
                dataIndex: 'debit',
                width: 150,
                render: (_: any, __: any, index: number) => (
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    value={entryLines[index].debit}
                    onChange={(value) => updateEntryLine(index, 'debit', value || 0)}
                  />
                ),
              },
              {
                title: 'الدائن',
                dataIndex: 'credit',
                width: 150,
                render: (_: any, __: any, index: number) => (
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    value={entryLines[index].credit}
                    onChange={(value) => updateEntryLine(index, 'credit', value || 0)}
                  />
                ),
              },
              {
                title: '',
                width: 50,
                render: (_: any, __: any, index: number) => (
                  <Button
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => removeEntryLine(index)}
                    disabled={entryLines.length <= 2}
                  />
                ),
              },
            ]}
          />
          <Button
            type="dashed"
            block
            icon={<PlusOutlined />}
            onClick={addEntryLine}
            style={{ marginTop: 16 }}
          >
            إضافة بند
          </Button>
          
          {/* Totals */}
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={8}>
              <Statistic
                title="إجمالي المدين"
                value={entryLines.reduce((sum, line) => sum + (line.debit || 0), 0)}
                suffix="ج.م"
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="إجمالي الدائن"
                value={entryLines.reduce((sum, line) => sum + (line.credit || 0), 0)}
                suffix="ج.م"
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="الفرق"
                value={Math.abs(
                  entryLines.reduce((sum, line) => sum + (line.debit || 0), 0) -
                  entryLines.reduce((sum, line) => sum + (line.credit || 0), 0)
                )}
                suffix="ج.م"
                valueStyle={{
                  color: Math.abs(
                    entryLines.reduce((sum, line) => sum + (line.debit || 0), 0) -
                    entryLines.reduce((sum, line) => sum + (line.credit || 0), 0)
                  ) > 0.01
                    ? '#ff4d4f'
                    : '#52c41a',
                }}
              />
            </Col>
          </Row>
        </Card>
      </Modal>

      {/* View Entry Modal */}
      <Modal
        title={`تفاصيل القيد: ${selectedEntry?.entry_number}`}
        open={!!selectedEntry}
        onCancel={() => setSelectedEntry(null)}
        footer={null}
        width={800}
      >
        {selectedEntry && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <p><strong>رقم القيد:</strong> {selectedEntry.entry_number}</p>
                <p><strong>التاريخ:</strong> {selectedEntry.entry_date}</p>
              </Col>
              <Col span={12}>
                <p><strong>الحالة:</strong> <Tag color={selectedEntry.status === 'posted' ? 'green' : 'orange'}>
                  {selectedEntry.status === 'posted' ? 'مرحل' : 'مسودة'}
                </Tag></p>
                <p><strong>المرجع:</strong> {selectedEntry.reference || '---'}</p>
              </Col>
            </Row>
            <p><strong>الوصف:</strong> {selectedEntry.description}</p>
            
            {selectedEntry.lines && (
              <Table
                dataSource={selectedEntry.lines}
                rowKey="id"
                pagination={false}
                columns={[
                  { title: 'الحساب', dataIndex: 'account_name' },
                  { title: 'المدين', dataIndex: 'debit', render: (v: number) => v.toLocaleString('ar-EG') },
                  { title: 'الدائن', dataIndex: 'credit', render: (v: number) => v.toLocaleString('ar-EG') },
                ]}
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AccountingPage;
