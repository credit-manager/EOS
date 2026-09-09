/**
 * EOS System — Projects Page
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
  Progress,
  Descriptions,
  Avatar,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ProjectOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { projectsApi } from '../services';
import type { Project, Task, TimeEntry } from '../types';

const { TabPane } = Tabs;
const { Title } = Typography;

const ProjectsPage: React.FC = () => {
  // =====================================================
  // State
  // =====================================================
  const [activeTab, setActiveTab] = useState('projects');
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalProjects, setTotalProjects] = useState(0);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  
  // Modals
  const [projectModalVisible, setProjectModalVisible] = useState(false);
  const [taskModalVisible, setTaskModalVisible] = useState(false);
  const [timeEntryModalVisible, setTimeEntryModalVisible] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  
  // Forms
  const [projectForm] = Form.useForm();
  const [taskForm] = Form.useForm();
  const [timeEntryForm] = Form.useForm();

  // =====================================================
  // Fetch Data
  // =====================================================

  const fetchProjects = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await projectsApi.listProjects({ page, page_size: pageSize });
      setProjects(result.data);
      setTotalProjects(result.total);
    } catch (error) {
      message.error('خطأ في تحميل المشاريع');
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async (projectId?: string) => {
    setLoading(true);
    try {
      if (projectId) {
        const result = await projectsApi.listTasks(projectId);
        setTasks(result.data);
      }
    } catch (error) {
      message.error('خطأ في تحميل المهام');
    } finally {
      setLoading(false);
    }
  };

  const fetchTimeEntries = async () => {
    setLoading(true);
    try {
      const result = await projectsApi.listTimeEntries();
      setTimeEntries(result.data);
    } catch (error) {
      message.error('خطأ في تحميل سجلات الوقت');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchTimeEntries();
  }, []);

  // =====================================================
  // Project Handlers
  // =====================================================

  const handleCreateProject = () => {
    setEditingProject(null);
    projectForm.resetFields();
    setProjectModalVisible(true);
  };

  const handleEditProject = (project: Project) => {
    setEditingProject(project);
    projectForm.setFieldsValue({
      ...project,
      start_date: project.start_date ? new Date(project.start_date) : null,
      end_date: project.end_date ? new Date(project.end_date) : null,
    });
    setProjectModalVisible(true);
  };

  const handleViewProject = (project: Project) => {
    setSelectedProject(project);
    fetchTasks(project.id);
  };

  const handleSaveProject = async () => {
    try {
      const values = await projectForm.validateFields();
      
      if (editingProject) {
        await projectsApi.updateProject(editingProject.id, values);
        message.success('تم تحديث المشروع بنجاح');
      } else {
        await projectsApi.createProject(values);
        message.success('تم إنشاء المشروع بنجاح');
      }
      
      setProjectModalVisible(false);
      fetchProjects();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ المشروع');
    }
  };

  const handleDeleteProject = async (id: string) => {
    try {
      await projectsApi.deleteProject(id);
      message.success('تم حذف المشروع بنجاح');
      fetchProjects();
    } catch (error) {
      message.error('حدث خطأ أثناء حذف المشروع');
    }
  };

  // =====================================================
  // Task Handlers
  // =====================================================

  const handleCreateTask = () => {
    taskForm.resetFields();
    setTaskModalVisible(true);
  };

  const handleSaveTask = async () => {
    try {
      const values = await taskForm.validateFields();
      
      if (selectedProject) {
        await projectsApi.createTask(selectedProject.id, values);
        message.success('تم إنشاء المهمة بنجاح');
        setTaskModalVisible(false);
        fetchTasks(selectedProject.id);
      }
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ المهمة');
    }
  };

  const handleUpdateTaskStatus = async (taskId: string, status: string) => {
    try {
      if (selectedProject) {
        await projectsApi.updateTaskStatus(selectedProject.id, taskId, status);
        message.success('تم تحديث حالة المهمة');
        fetchTasks(selectedProject.id);
      }
    } catch (error) {
      message.error('حدث خطأ أثناء تحديث الحالة');
    }
  };

  // =====================================================
  // Time Entry Handlers
  // =====================================================

  const handleCreateTimeEntry = () => {
    timeEntryForm.resetFields();
    setTimeEntryModalVisible(true);
  };

  const handleSaveTimeEntry = async () => {
    try {
      const values = await timeEntryForm.validateFields();
      await projectsApi.createTimeEntry(values);
      message.success('تم تسجيل الوقت بنجاح');
      setTimeEntryModalVisible(false);
      fetchTimeEntries();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ البيانات');
    }
  };

  // =====================================================
  // Table Columns
  // =====================================================

  const projectColumns = [
    {
      title: 'المشروع',
      key: 'project',
      render: (_: any, record: Project) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{record.name}</div>
          {record.name_ar && (
            <div style={{ color: '#8c8c8c', fontSize: 12 }}>{record.name_ar}</div>
          )}
        </div>
      ),
    },
    {
      title: 'التقدم',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => (
        <Progress percent={progress} size="small" />
      ),
    },
    {
      title: 'الحالة',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          planning: { color: 'blue', text: 'التخطيط' },
          in_progress: { color: 'orange', text: 'قيد التنفيذ' },
          on_hold: { color: 'red', text: 'متوقف' },
          completed: { color: 'green', text: 'مكتمل' },
          cancelled: { color: 'default', text: 'ملغي' },
        };
        const { color, text } = statusMap[status] || { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: 'الميزانية',
      dataIndex: 'budget',
      key: 'budget',
      render: (budget: number) => budget ? (
        <span style={{ fontWeight: 'bold' }}>
          {budget.toLocaleString('ar-EG')} ج.م
        </span>
      ) : '---',
    },
    {
      title: 'تاريخ البداية',
      dataIndex: 'start_date',
      key: 'start_date',
    },
    {
      title: 'تاريخ النهاية',
      dataIndex: 'end_date',
      key: 'end_date',
      render: (date: string) => date || '---',
    },
    {
      title: 'إجراءات',
      key: 'actions',
      render: (_: any, record: Project) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewProject(record)}
          />
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditProject(record)}
          />
          <Popconfirm
            title="هل أنت متأكد من حذف هذا المشروع؟"
            onConfirm={() => handleDeleteProject(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const taskColumns = [
    {
      title: 'المهمة',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <span style={{ fontWeight: 'bold' }}>{name}</span>
      ),
    },
    {
      title: 'المسؤول',
      dataIndex: 'assignee_name',
      key: 'assignee_name',
      render: (name: string) => name ? (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          {name}
        </Space>
      ) : '---',
    },
    {
      title: 'الأولوية',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => {
        const priorityMap: Record<string, { color: string; text: string }> = {
          low: { color: 'green', text: 'منخفضة' },
          medium: { color: 'orange', text: 'متوسطة' },
          high: { color: 'red', text: 'عالية' },
          urgent: { color: 'magenta', text: 'عاجلة' },
        };
        const { color, text } = priorityMap[priority] || { color: 'default', text: priority };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: 'الحالة',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: Task) => {
        return (
          <Select
            value={status}
            onChange={(value) => handleUpdateTaskStatus(record.id, value)}
            style={{ width: 130 }}
            size="small"
          >
            <Select.Option value="todo">قيد الانتظار</Select.Option>
            <Select.Option value="in_progress">قيد التنفيذ</Select.Option>
            <Select.Option value="review">قيد المراجعة</Select.Option>
            <Select.Option value="done">مكتمل</Select.Option>
          </Select>
        );
      },
    },
    {
      title: 'التاريخ المستهدف',
      dataIndex: 'due_date',
      key: 'due_date',
      render: (date: string) => date || '---',
    },
    {
      title: 'الوقت المقدر',
      dataIndex: 'estimated_hours',
      key: 'estimated_hours',
      render: (hours: number) => hours ? `${hours} ساعة` : '---',
    },
    {
      title: 'الوقت الفعلي',
      dataIndex: 'actual_hours',
      key: 'actual_hours',
      render: (hours: number) => hours ? `${hours} ساعة` : '---',
    },
  ];

  // =====================================================
  // Render
  // =====================================================

  return (
    <div>
      <Title level={4}>
        <ProjectOutlined /> إدارة المشاريع
      </Title>

      {/* Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="إجمالي المشاريع"
              value={totalProjects}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="قيد التنفيذ"
              value={projects.filter(p => p.status === 'in_progress').length}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="مكتملة"
              value={projects.filter(p => p.status === 'completed').length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="ساعات العمل"
              value={timeEntries.reduce((sum, entry) => sum + entry.hours, 0)}
              prefix={<ClockCircleOutlined />}
              suffix="ساعة"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="المشاريع" key="projects">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateProject}>
                  إنشاء مشروع
                </Button>
                <Select placeholder="الحالة" style={{ width: 150 }} allowClear>
                  <Select.Option value="planning">التخطيط</Select.Option>
                  <Select.Option value="in_progress">قيد التنفيذ</Select.Option>
                  <Select.Option value="completed">مكتمل</Select.Option>
                </Select>
              </Space>
            </div>
            <Table
              columns={projectColumns}
              dataSource={projects}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalProjects,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} مشروع`,
              }}
            />
          </TabPane>

          <TabPane tab="الوقت" key="time">
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateTimeEntry}>
                تسجيل وقت
              </Button>
            </div>
            <Table
              dataSource={timeEntries}
              rowKey="id"
              columns={[
                {
                  title: 'المشروع',
                  dataIndex: 'project_id',
                  key: 'project_id',
                },
                {
                  title: 'المهمة',
                  dataIndex: 'task_id',
                  key: 'task_id',
                },
                {
                  title: 'التاريخ',
                  dataIndex: 'date',
                  key: 'date',
                },
                {
                  title: 'الساعات',
                  dataIndex: 'hours',
                  key: 'hours',
                  render: (hours: number) => `${hours} ساعة`,
                },
                {
                  title: 'الوصف',
                  dataIndex: 'description',
                  key: 'description',
                  ellipsis: true,
                },
              ]}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Project Modal */}
      <Modal
        title={editingProject ? 'تعديل المشروع' : 'إنشاء مشروع جديد'}
        open={projectModalVisible}
        onOk={handleSaveProject}
        onCancel={() => setProjectModalVisible(false)}
        width={700}
      >
        <Form form={projectForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="اسم المشروع"
                rules={[{ required: true, message: 'أدخل اسم المشروع' }]}
              >
                <Input placeholder="اسم المشروع" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="name_ar" label="اسم المشروع (عربي)">
                <Input placeholder="اسم المشروع بالعربي" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="الوصف">
            <Input.TextArea rows={3} placeholder="وصف المشروع" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="start_date"
                label="تاريخ البداية"
                rules={[{ required: true, message: 'اختر تاريخ البداية' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="تاريخ النهاية">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="budget" label="الميزانية">
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  placeholder="0"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="client_id" label="العميل">
                <Select placeholder="اختر العميل" allowClear>
                  {/* Add customers here */}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="manager_id" label="مدير المشروع">
            <Select placeholder="اختر مدير المشروع" allowClear>
              {/* Add employees here */}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Task Modal */}
      <Modal
        title="إضافة مهمة جديدة"
        open={taskModalVisible}
        onOk={handleSaveTask}
        onCancel={() => setTaskModalVisible(false)}
        width={600}
      >
        <Form form={taskForm} layout="vertical">
          <Form.Item
            name="name"
            label="اسم المهمة"
            rules={[{ required: true, message: 'أدخل اسم المهمة' }]}
          >
            <Input placeholder="اسم المهمة" />
          </Form.Item>
          <Form.Item name="description" label="الوصف">
            <Input.TextArea rows={3} placeholder="وصف المهمة" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="assignee_id" label="المسؤول">
                <Select placeholder="اختر المسؤول" allowClear>
                  {/* Add employees here */}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="priority" label="الأولوية">
                <Select placeholder="اختر الأولوية">
                  <Select.Option value="low">منخفضة</Select.Option>
                  <Select.Option value="medium">متوسطة</Select.Option>
                  <Select.Option value="high">عالية</Select.Option>
                  <Select.Option value="urgent">عاجلة</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="start_date" label="تاريخ البداية">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="due_date" label="تاريخ الاستحقاق">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="estimated_hours" label="الوقت المقدر (ساعات)">
            <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Time Entry Modal */}
      <Modal
        title="تسجيل وقت"
        open={timeEntryModalVisible}
        onOk={handleSaveTimeEntry}
        onCancel={() => setTimeEntryModalVisible(false)}
      >
        <Form form={timeEntryForm} layout="vertical">
          <Form.Item
            name="project_id"
            label="المشروع"
            rules={[{ required: true, message: 'اختر المشروع' }]}
          >
            <Select placeholder="اختر المشروع">
              {projects.map((project) => (
                <Select.Option key={project.id} value={project.id}>
                  {project.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="task_id"
            label="المهمة"
            rules={[{ required: true, message: 'اختر المهمة' }]}
          >
            <Select placeholder="اختر المهمة">
              {tasks.map((task) => (
                <Select.Option key={task.id} value={task.id}>
                  {task.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="date"
            label="التاريخ"
            rules={[{ required: true, message: 'اختر التاريخ' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="hours"
            label="الساعات"
            rules={[{ required: true, message: 'أدخل عدد الساعات' }]}
          >
            <InputNumber style={{ width: '100%' }} min={0.5} step={0.5} placeholder="0" />
          </Form.Item>
          <Form.Item name="description" label="الوصف">
            <Input.TextArea rows={2} placeholder="وصف العمل المنجز" />
          </Form.Item>
        </Form>
      </Modal>

      {/* View Project Modal */}
      <Modal
        title={`تفاصيل المشروع: ${selectedProject?.name}`}
        open={!!selectedProject}
        onCancel={() => setSelectedProject(null)}
        footer={null}
        width={900}
      >
        {selectedProject && (
          <>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="اسم المشروع">{selectedProject.name}</Descriptions.Item>
              <Descriptions.Item label="الحالة">
                <Tag color={selectedProject.status === 'completed' ? 'green' : 'blue'}>
                  {selectedProject.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="التقدم">
                <Progress percent={selectedProject.progress} />
              </Descriptions.Item>
              <Descriptions.Item label="الميزانية">
                {selectedProject.budget ? `${selectedProject.budget.toLocaleString('ar-EG')} ج.م` : '---'}
              </Descriptions.Item>
              <Descriptions.Item label="تاريخ البداية">{selectedProject.start_date}</Descriptions.Item>
              <Descriptions.Item label="تاريخ النهاية">{selectedProject.end_date || '---'}</Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 24 }}>
              <Space>
                <Title level={5}>المهام</Title>
                <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreateTask}>
                  إضافة مهمة
                </Button>
              </Space>
              <Table
                columns={taskColumns}
                dataSource={tasks}
                rowKey="id"
                loading={loading}
                pagination={false}
                style={{ marginTop: 16 }}
              />
            </div>
          </>
        )}
      </Modal>
    </div>
  );
};

export default ProjectsPage;
