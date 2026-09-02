import React from 'react'
import { Card, Table, Button, Tag, Space } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

function EntitiesPage() {
  const { t } = useTranslation()

  const sampleData = [
    { key: '1', name: 'customers', type: 'Sales', fields: 12, status: 'active' },
    { key: '2', name: 'products', type: 'Inventory', fields: 15, status: 'active' },
    { key: '3', name: 'invoices', type: 'Accounting', fields: 18, status: 'active' },
    { key: '4', name: 'employees', type: 'HR', fields: 20, status: 'active' },
    { key: '5', name: 'projects', type: 'Projects', fields: 16, status: 'active' },
  ]

  const columns = [
    {
      title: t('entity_name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'النوع',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: t('fields'),
      dataIndex: 'fields',
      key: 'fields',
      sorter: (a, b) => a.fields - b.fields,
    },
    {
      title: 'الحالة',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>
          {status === 'active' ? 'نشط' : 'غير نشط'}
        </Tag>
      ),
    },
    {
      title: 'الإجراءات',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button type="link" icon={<EditOutlined />} />
          <Button type="link" danger icon={<DeleteOutlined />} />
        </Space>
      ),
    },
  ]

  return (
    <div className="fade-in">
      <Card
        title={t('entities')}
        extra={
          <Button type="primary" icon={<PlusOutlined />}>
            {t('create')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={sampleData}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  )
}

export default EntitiesPage
