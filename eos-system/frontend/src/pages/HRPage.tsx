/**
 * EOS System — HR Page
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
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  TeamOutlined,
  UserOutlined,
  BankOutlined,
  ClockCircleOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { hrApi } from '../services';
import type { Employee, Department, AttendanceRecord } from '../types';

const { TabPane } = Tabs;
const { Title } = Typography;

const HRPage: React.FC = () => {
  // =====================================================
  // State
  // =====================================================
  const [activeTab, setActiveTab] = useState('employees');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalEmployees, setTotalEmployees] = useState(0);
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  
  // Modals
  const [employeeModalVisible, setEmployeeModalVisible] = useState(false);
  const [departmentModalVisible, setDepartmentModalVisible] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  
  // Forms
  const [employeeForm] = Form.useForm();
  const [departmentForm] = Form.useForm();

  // =====================================================
  // Fetch Data
  // =====================================================

  const fetchEmployees = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await hrApi.listEmployees({ page, page_size: pageSize });
      setEmployees(result.data);
      setTotalEmployees(result.total);
    } catch (error) {
      message.error('خطأ في تحميل الموظفين');
    } finally {
      setLoading(false);
    }
  };

  const fetchDepartments = async () => {
    try {
      const result = await hrApi.listDepartments();
      setDepartments(result);
    } catch (error) {
      message.error('خطأ في تحميل الأقسام');
    }
  };

  const fetchAttendance = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await hrApi.listAttendance({ page, page_size: pageSize });
      setAttendance(result.data);
    } catch (error) {
      message.error('خطأ في تحميل سجلات الحضور');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
    fetchDepartments();
    fetchAttendance();
  }, []);

  // =====================================================
  // Employee Handlers
  // =====================================================

  const handleCreateEmployee = () => {
    setEditingEmployee(null);
    employeeForm.resetFields();
    setEmployeeModalVisible(true);
  };

  const handleEditEmployee = (employee: Employee) => {
    setEditingEmployee(employee);
    employeeForm.setFieldsValue({
      ...employee,
      hire_date: employee.hire_date ? new Date(employee.hire_date) : null,
    });
    setEmployeeModalVisible(true);
  };

  const handleViewEmployee = (employee: Employee) => {
    setSelectedEmployee(employee);
  };

  const handleSaveEmployee = async () => {
    try {
      const values = await employeeForm.validateFields();
      
      if (editingEmployee) {
        await hrApi.updateEmployee(editingEmployee.id, values);
        message.success('تم تحديث بيانات الموظف بنجاح');
      } else {
        await hrApi.createEmployee(values);
        message.success('تم إضافة الموظف بنجاح');
      }
      
      setEmployeeModalVisible(false);
      fetchEmployees();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ بيانات الموظف');
    }
  };

  const handleDeleteEmployee = async (id: string) => {
    try {
      await hrApi.deleteEmployee(id);
      message.success('تم حذف الموظف بنجاح');
      fetchEmployees();
    } catch (error) {
      message.error('حدث خطأ أثناء حذف الموظف');
    }
  };

  // =====================================================
  // Department Handlers
  // =====================================================

  const handleCreateDepartment = () => {
    departmentForm.resetFields();
    setDepartmentModalVisible(true);
  };

  const handleSaveDepartment = async () => {
    try {
      const values = await departmentForm.validateFields();
      await hrApi.createDepartment(values);
      message.success('تم إنشاء القسم بنجاح');
      setDepartmentModalVisible(false);
      fetchDepartments();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ القسم');
    }
  };

  // =====================================================
  // Table Columns
  // =====================================================

  const employeeColumns = [
    {
      title: 'الموظف',
      key: 'employee',
      render: (_: any, record: Employee) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 'bold' }}>{record.first_name} {record.last_name}</div>
            <div style={{ color: '#8c8c8c', fontSize: 12 }}>{record.email}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'رقم الموظف',
      dataIndex: 'employee_id',
      key: 'employee_id',
      width: 120,
    },
    {
      title: 'القسم',
      dataIndex: 'department_id',
      key: 'department_id',
      render: (deptId: string) => {
        const dept = departments.find(d => d.id === deptId);
        return dept ? dept.name : '---';
      },
    },
    {
      title: 'تاريخ التعيين',
      dataIndex: 'hire_date',
      key: 'hire_date',
      width: 120,
    },
    {
      title: 'الراتب',
      dataIndex: 'salary',
      key: 'salary',
      render: (salary: number) => (
        <span style={{ fontWeight: 'bold' }}>
          {salary.toLocaleString('ar-EG')} ج.م
        </span>
      ),
    },
    {
      title: 'الحالة',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>
          {status === 'active' ? 'نشط' : 'غير نشط'}
        </Tag>
      ),
    },
    {
      title: 'إجراءات',
      key: 'actions',
      render: (_: any, record: Employee) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewEmployee(record)}
          />
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditEmployee(record)}
          />
          <Popconfirm
            title="هل أنت متأكد من حذف هذا الموظف؟"
            onConfirm={() => handleDeleteEmployee(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const departmentColumns = [
    {
      title: 'الكود',
      dataIndex: 'code',
      key: 'code',
      width: 100,
    },
    {
      title: 'اسم القسم',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'الاسم (عربي)',
      dataIndex: 'name_ar',
      key: 'name_ar',
    },
    {
      title: 'عدد الموظفين',
      dataIndex: 'employee_count',
      key: 'employee_count',
      render: (count: number) => (
        <Tag color="blue">{count} موظف</Tag>
      ),
    },
  ];

  // =====================================================
  // Render
  // =====================================================

  return (
    <div>
      <Title level={4}>
        <TeamOutlined /> الموارد البشرية
      </Title>

      {/* Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="إجمالي الموظفين"
              value={totalEmployees}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="الأقسام"
              value={departments.length}
              prefix={<BankOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="الحضور اليوم"
              value={attendance.filter(a => a.status === 'present').length}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="الرواتب الشهرية"
              value={employees.reduce((sum, emp) => sum + emp.salary, 0)}
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
          <TabPane tab="الموظفين" key="employees">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateEmployee}>
                  إضافة موظف
                </Button>
                <Input.Search placeholder="بحث في الموظفين" style={{ width: 300 }} />
              </Space>
            </div>
            <Table
              columns={employeeColumns}
              dataSource={employees}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalEmployees,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} موظف`,
              }}
            />
          </TabPane>

          <TabPane tab="الأقسام" key="departments">
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateDepartment}>
                إضافة قسم
              </Button>
            </div>
            <Table
              columns={departmentColumns}
              dataSource={departments}
              rowKey="id"
              pagination={false}
            />
          </TabPane>

          <TabPane tab="الحضور والانصراف" key="attendance">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <DatePicker.RangePicker />
                <Select placeholder="الحالة" style={{ width: 120 }} allowClear>
                  <Select.Option value="present">حاضر</Select.Option>
                  <Select.Option value="absent">غائب</Select.Option>
                  <Select.Option value="late">متأخر</Select.Option>
                  <Select.Option value="leave">إجازة</Select.Option>
                </Select>
              </Space>
            </div>
            <Table
              dataSource={attendance}
              rowKey="id"
              columns={[
                {
                  title: 'الموظف',
                  key: 'employee',
                  render: (_: any, record: AttendanceRecord) => (
                    <span>{record.employee_id}</span>
                  ),
                },
                { title: 'التاريخ', dataIndex: 'date', key: 'date' },
                {
                  title: 'وقت الحضور',
                  dataIndex: 'clock_in',
                  key: 'clock_in',
                  render: (time: string) => time ? new Date(time).toLocaleTimeString('ar-EG') : '---',
                },
                {
                  title: 'وقت الانصراف',
                  dataIndex: 'clock_out',
                  key: 'clock_out',
                  render: (time: string) => time ? new Date(time).toLocaleTimeString('ar-EG') : '---',
                },
                {
                  title: 'الحالة',
                  dataIndex: 'status',
                  key: 'status',
                  render: (status: string) => {
                    const statusMap: Record<string, { color: string; text: string }> = {
                      present: { color: 'green', text: 'حاضر' },
                      absent: { color: 'red', text: 'غائب' },
                      late: { color: 'orange', text: 'متأخر' },
                      leave: { color: 'blue', text: 'إجازة' },
                    };
                    const { color, text } = statusMap[status] || { color: 'default', text: status };
                    return <Tag color={color}>{text}</Tag>;
                  },
                },
                {
                  title: 'ساعات العمل',
                  dataIndex: 'hours_worked',
                  key: 'hours_worked',
                  render: (hours: number) => `${hours.toFixed(1)} ساعة`,
                },
              ]}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Employee Modal */}
      <Modal
        title={editingEmployee ? 'تعديل بيانات الموظف' : 'إضافة موظف جديد'}
        open={employeeModalVisible}
        onOk={handleSaveEmployee}
        onCancel={() => setEmployeeModalVisible(false)}
        width={700}
      >
        <Form form={employeeForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="employee_id"
                label="رقم الموظف"
                rules={[{ required: true, message: 'أدخل رقم الموظف' }]}
              >
                <Input placeholder="مثال: EMP-001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="department_id"
                label="القسم"
                rules={[{ required: true, message: 'اختر القسم' }]}
              >
                <Select placeholder="اختر القسم">
                  {departments.map((dept) => (
                    <Select.Option key={dept.id} value={dept.id}>
                      {dept.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
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
              <Form.Item
                name="first_name_ar"
                label="الاسم الأول (عربي)"
              >
                <Input placeholder="الاسم الأول بالعربي" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="last_name_ar"
                label="اسم العائلة (عربي)"
              >
                <Input placeholder="اسم العائلة بالعربي" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="email"
                label="البريد الإلكتروني"
                rules={[
                  { required: true, message: 'أدخل البريد الإلكتروني' },
                  { type: 'email', message: 'البريد الإلكتروني غير صحيح' },
                ]}
              >
                <Input placeholder="email@example.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="رقم الهاتف">
                <Input placeholder="+201234567890" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="hire_date"
                label="تاريخ التعيين"
                rules={[{ required: true, message: 'اختر تاريخ التعيين' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="salary"
                label="الراتب"
                rules={[{ required: true, message: 'أدخل الراتب' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  placeholder="0"
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="national_id" label="رقم البطاقة الشخصية">
                <Input placeholder="رقم البطاقة الشخصية" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="social_insurance_number" label="رقم التأمينات">
                <Input placeholder="رقم التأمينات الاجتماعية" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Department Modal */}
      <Modal
        title="إضافة قسم جديد"
        open={departmentModalVisible}
        onOk={handleSaveDepartment}
        onCancel={() => setDepartmentModalVisible(false)}
      >
        <Form form={departmentForm} layout="vertical">
          <Form.Item
            name="code"
            label="كود القسم"
            rules={[{ required: true, message: 'أدخل كود القسم' }]}
          >
            <Input placeholder="مثال: HR, IT, SALES" />
          </Form.Item>
          <Form.Item
            name="name"
            label="اسم القسم (إنجليزي)"
            rules={[{ required: true, message: 'أدخل اسم القسم' }]}
          >
            <Input placeholder="Department Name" />
          </Form.Item>
          <Form.Item
            name="name_ar"
            label="اسم القسم (عربي)"
            rules={[{ required: true, message: 'أدخل اسم القسم بالعربي' }]}
          >
            <Input placeholder="اسم القسم" />
          </Form.Item>
          <Form.Item name="parent_id" label="القسم الأب">
            <Select placeholder="اختر القسم الأب" allowClear>
              {departments.map((dept) => (
                <Select.Option key={dept.id} value={dept.id}>
                  {dept.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* View Employee Modal */}
      <Modal
        title={`بيانات الموظف: ${selectedEmployee?.first_name} ${selectedEmployee?.last_name}`}
        open={!!selectedEmployee}
        onCancel={() => setSelectedEmployee(null)}
        footer={null}
        width={700}
      >
        {selectedEmployee && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="رقم الموظف">{selectedEmployee.employee_id}</Descriptions.Item>
            <Descriptions.Item label="الحالة">
              <Tag color={selectedEmployee.status === 'active' ? 'green' : 'red'}>
                {selectedEmployee.status === 'active' ? 'نشط' : 'غير نشط'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="الاسم">{selectedEmployee.first_name} {selectedEmployee.last_name}</Descriptions.Item>
            <Descriptions.Item label="الاسم (عربي)">{selectedEmployee.first_name_ar} {selectedEmployee.last_name_ar}</Descriptions.Item>
            <Descriptions.Item label="البريد الإلكتروني">{selectedEmployee.email}</Descriptions.Item>
            <Descriptions.Item label="الهاتف">{selectedEmployee.phone || '---'}</Descriptions.Item>
            <Descriptions.Item label="القسم">
              {departments.find(d => d.id === selectedEmployee.department_id)?.name || '---'}
            </Descriptions.Item>
            <Descriptions.Item label="تاريخ التعيين">{selectedEmployee.hire_date}</Descriptions.Item>
            <Descriptions.Item label="الراتب">{selectedEmployee.salary.toLocaleString('ar-EG')} ج.م</Descriptions.Item>
            <Descriptions.Item label="رقم البطاقة">{selectedEmployee.national_id || '---'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default HRPage;
