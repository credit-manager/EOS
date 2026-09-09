/**
 * EOS System — Inventory Page
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
  message,
  Popconfirm,
  Typography,
  Badge,
  Alert,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ShopOutlined,
  InboxOutlined,
  WarningOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  SwapOutlined,
  BarcodeOutlined,
} from '@ant-design/icons';
import { inventoryApi } from '../services';
import type { Product, Warehouse, StockMovement, LowStockAlert } from '../types';

const { TabPane } = Tabs;
const { Title } = Typography;

const InventoryPage: React.FC = () => {
  // =====================================================
  // State
  // =====================================================
  const [activeTab, setActiveTab] = useState('products');
  const [products, setProducts] = useState<Product[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [lowStockAlerts, setLowStockAlerts] = useState<LowStockAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalProducts, setTotalProducts] = useState(0);
  const [totalMovements, setTotalMovements] = useState(0);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  
  // Modals
  const [productModalVisible, setProductModalVisible] = useState(false);
  const [warehouseModalVisible, setWarehouseModalVisible] = useState(false);
  const [movementModalVisible, setMovementModalVisible] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  
  // Forms
  const [productForm] = Form.useForm();
  const [warehouseForm] = Form.useForm();
  const [movementForm] = Form.useForm();

  // =====================================================
  // Fetch Data
  // =====================================================

  const fetchProducts = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await inventoryApi.listProducts({ page, page_size: pageSize });
      setProducts(result.data);
      setTotalProducts(result.total);
    } catch (error) {
      message.error('خطأ في تحميل المنتجات');
    } finally {
      setLoading(false);
    }
  };

  const fetchWarehouses = async () => {
    try {
      const result = await inventoryApi.listWarehouses();
      setWarehouses(result);
    } catch (error) {
      message.error('خطأ في تحميل المخازن');
    }
  };

  const fetchMovements = async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const result = await inventoryApi.listStockMovements({ page, page_size: pageSize });
      setMovements(result.data);
      setTotalMovements(result.total);
    } catch (error) {
      message.error('خطأ في تحميل الحركات');
    } finally {
      setLoading(false);
    }
  };

  const fetchLowStockAlerts = async () => {
    try {
      const result = await inventoryApi.getLowStockAlerts();
      setLowStockAlerts(result);
    } catch (error) {
      message.error('خطأ في تحميل التنبيهات');
    }
  };

  useEffect(() => {
    fetchProducts();
    fetchWarehouses();
    fetchMovements();
    fetchLowStockAlerts();
  }, []);

  // =====================================================
  // Product Handlers
  // =====================================================

  const handleCreateProduct = () => {
    setEditingProduct(null);
    productForm.resetFields();
    setProductModalVisible(true);
  };

  const handleEditProduct = (product: Product) => {
    setEditingProduct(product);
    productForm.setFieldsValue(product);
    setProductModalVisible(true);
  };

  const handleViewProduct = (product: Product) => {
    setSelectedProduct(product);
  };

  const handleSaveProduct = async () => {
    try {
      const values = await productForm.validateFields();
      
      if (editingProduct) {
        await inventoryApi.updateProduct(editingProduct.id, values);
        message.success('تم تحديث المنتج بنجاح');
      } else {
        await inventoryApi.createProduct(values);
        message.success('تم إنشاء المنتج بنجاح');
      }
      
      setProductModalVisible(false);
      fetchProducts();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ المنتج');
    }
  };

  const handleDeleteProduct = async (id: string) => {
    try {
      await inventoryApi.deleteProduct(id);
      message.success('تم حذف المنتج بنجاح');
      fetchProducts();
    } catch (error) {
      message.error('حدث خطأ أثناء حذف المنتج');
    }
  };

  // =====================================================
  // Warehouse Handlers
  // =====================================================

  const handleCreateWarehouse = () => {
    warehouseForm.resetFields();
    setWarehouseModalVisible(true);
  };

  const handleSaveWarehouse = async () => {
    try {
      const values = await warehouseForm.validateFields();
      await inventoryApi.createWarehouse(values);
      message.success('تم إنشاء المخزن بنجاح');
      setWarehouseModalVisible(false);
      fetchWarehouses();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ المخزن');
    }
  };

  // =====================================================
  // Movement Handlers
  // =====================================================

  const handleCreateMovement = () => {
    movementForm.resetFields();
    setMovementModalVisible(true);
  };

  const handleSaveMovement = async () => {
    try {
      const values = await movementForm.validateFields();
      await inventoryApi.createStockMovement(values);
      message.success('تم تسجيل الحركة بنجاح');
      setMovementModalVisible(false);
      fetchMovements();
      fetchProducts();
      fetchLowStockAlerts();
    } catch (error) {
      message.error('حدث خطأ أثناء حفظ الحركة');
    }
  };

  // =====================================================
  // Table Columns
  // =====================================================

  const productColumns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      render: (sku: string) => <Tag icon={<BarcodeOutlined />}>{sku}</Tag>,
    },
    {
      title: 'اسم المنتج',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Product) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{name}</div>
          <div style={{ color: '#8c8c8c', fontSize: 12 }}>{record.name_ar}</div>
        </div>
      ),
    },
    {
      title: 'السعر',
      dataIndex: 'unit_price',
      key: 'unit_price',
      render: (price: number) => (
        <span style={{ fontWeight: 'bold' }}>
          {price.toLocaleString('ar-EG')} ج.م
        </span>
      ),
    },
    {
      title: 'المخزون',
      dataIndex: 'current_stock',
      key: 'current_stock',
      render: (stock: number, record: Product) => (
        <div>
          <span style={{ 
            fontWeight: 'bold',
            color: stock <= record.min_stock ? '#ff4d4f' : '#52c41a'
          }}>
            {stock}
          </span>
          {stock <= record.min_stock && (
            <Tag color="red" style={{ marginLeft: 8 }}>
              <WarningOutlined /> منخفض
            </Tag>
          )}
        </div>
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
      render: (_: any, record: Product) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewProduct(record)}
          />
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditProduct(record)}
          />
          <Popconfirm
            title="هل أنت متأكد من حذف هذا المنتج؟"
            onConfirm={() => handleDeleteProduct(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const movementColumns = [
    {
      title: 'التاريخ',
      dataIndex: 'movement_date',
      key: 'movement_date',
      width: 120,
    },
    {
      title: 'النوع',
      dataIndex: 'movement_type',
      key: 'movement_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
          in: { color: 'green', icon: <ArrowUpOutlined />, text: 'وارد' },
          out: { color: 'red', icon: <ArrowDownOutlined />, text: 'صادر' },
          transfer: { color: 'blue', icon: <SwapOutlined />, text: 'تحويل' },
          adjustment: { color: 'orange', icon: <SwapOutlined />, text: 'تسوية' },
        };
        const { color, icon, text } = typeMap[type] || { color: 'default', icon: null, text: type };
        return <Tag color={color} icon={icon}>{text}</Tag>;
      },
    },
    {
      title: 'المنتج',
      dataIndex: 'product_id',
      key: 'product_id',
    },
    {
      title: 'الكمية',
      dataIndex: 'quantity',
      key: 'quantity',
      render: (qty: number, record: StockMovement) => (
        <span style={{ 
          fontWeight: 'bold',
          color: record.movement_type === 'in' ? '#52c41a' : '#ff4d4f'
        }}>
          {record.movement_type === 'in' ? '+' : '-'}{qty}
        </span>
      ),
    },
    {
      title: 'المخزن',
      dataIndex: 'warehouse_id',
      key: 'warehouse_id',
    },
  ];

  // =====================================================
  // Render
  // =====================================================

  return (
    <div>
      <Title level={4}>
        <ShopOutlined /> المخزون والمشتريات
      </Title>

      {/* Low Stock Alert */}
      {lowStockAlerts.length > 0 && (
        <Alert
          message={`تنبيه: ${lowStockAlerts.length} منتجات منخفضة المخزون`}
          description={
            <div>
              {lowStockAlerts.slice(0, 3).map((alert) => (
                <div key={alert.product_id}>
                  {alert.name} ({alert.sku}): {alert.current_stock} / {alert.min_stock}
                </div>
              ))}
              {lowStockAlerts.length > 3 && (
                <div>و {lowStockAlerts.length - 3} منتجات أخرى...</div>
              )}
            </div>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="إجمالي المنتجات"
              value={totalProducts}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="الحركات"
              value={totalMovements}
              prefix={<InboxOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="المخازن"
              value={warehouses.length}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="تنبيهات المخزون"
              value={lowStockAlerts.length}
              prefix={<WarningOutlined />}
              valueStyle={{ color: lowStockAlerts.length > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="المنتجات" key="products">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateProduct}>
                  إضافة منتج
                </Button>
                <Input.Search placeholder="بحث في المنتجات" style={{ width: 300 }} />
              </Space>
            </div>
            <Table
              columns={productColumns}
              dataSource={products}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalProducts,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} منتج`,
              }}
            />
          </TabPane>

          <TabPane tab="الحركات" key="movements">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateMovement}>
                  تسجيل حركة
                </Button>
                <Select placeholder="نوع الحركة" style={{ width: 150 }} allowClear>
                  <Select.Option value="in">وارد</Select.Option>
                  <Select.Option value="out">صادر</Select.Option>
                  <Select.Option value="transfer">تحويل</Select.Option>
                  <Select.Option value="adjustment">تسوية</Select.Option>
                </Select>
              </Space>
            </div>
            <Table
              columns={movementColumns}
              dataSource={movements}
              rowKey="id"
              loading={loading}
              pagination={{
                total: totalMovements,
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `إجمالي ${total} حركة`,
              }}
            />
          </TabPane>

          <TabPane tab="المخازن" key="warehouses">
            <div style={{ marginBottom: 16 }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateWarehouse}>
                إضافة مخزن
              </Button>
            </div>
            <Table
              dataSource={warehouses}
              rowKey="id"
              columns={[
                { title: 'الكود', dataIndex: 'code', key: 'code' },
                { title: 'الاسم', dataIndex: 'name', key: 'name' },
                { title: 'الاسم (عربي)', dataIndex: 'name_ar', key: 'name_ar' },
                { title: 'العنوان', dataIndex: 'address', key: 'address' },
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
              ]}
            />
          </TabPane>

          <TabPane 
            tab={
              <Badge count={lowStockAlerts.length} offset={[10, 0]}>
                تنبيهات المخزون
              </Badge>
            } 
            key="alerts"
          >
            <Table
              dataSource={lowStockAlerts}
              rowKey="product_id"
              columns={[
                { title: 'SKU', dataIndex: 'sku', key: 'sku' },
                { title: 'المنتج', dataIndex: 'name', key: 'name' },
                { title: 'المخزون الحالي', dataIndex: 'current_stock', key: 'current_stock' },
                { title: 'الحد الأدنى', dataIndex: 'min_stock', key: 'min_stock' },
                {
                  title: 'الحالة',
                  key: 'status',
                  render: (_: any, _record: LowStockAlert) => (
                    <Tag color="red">
                      <WarningOutlined /> يلزم إعادة توريد
                    </Tag>
                  ),
                },
              ]}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Product Modal */}
      <Modal
        title={editingProduct ? 'تعديل المنتج' : 'إضافة منتج جديد'}
        open={productModalVisible}
        onOk={handleSaveProduct}
        onCancel={() => setProductModalVisible(false)}
        width={700}
      >
        <Form form={productForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="sku"
                label="SKU"
                rules={[{ required: true, message: 'أدخل كود المنتج' }]}
              >
                <Input placeholder="مثال: PRD-001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="barcode" label="الباركود">
                <Input placeholder="رقم الباركود" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="اسم المنتج (إنجليزي)"
                rules={[{ required: true, message: 'أدخل اسم المنتج' }]}
              >
                <Input placeholder="Product Name" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="name_ar"
                label="اسم المنتج (عربي)"
                rules={[{ required: true, message: 'أدخل اسم المنتج بالعربي' }]}
              >
                <Input placeholder="اسم المنتج" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="unit_price"
                label="سعر البيع"
                rules={[{ required: true, message: 'أدخل سعر البيع' }]}
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
              <Form.Item
                name="cost_price"
                label="سعر التكلفة"
                rules={[{ required: true, message: 'أدخل سعر التكلفة' }]}
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
            <Col span={8}>
              <Form.Item name="min_stock" label="الحد الأدنى">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_stock" label="الحد الأقصى">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="category_id" label="الفئة">
                <Select placeholder="اختر الفئة" allowClear>
                  {/* Add categories here */}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="الوصف">
            <Input.TextArea rows={3} placeholder="وصف المنتج" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Warehouse Modal */}
      <Modal
        title="إضافة مخزن جديد"
        open={warehouseModalVisible}
        onOk={handleSaveWarehouse}
        onCancel={() => setWarehouseModalVisible(false)}
      >
        <Form form={warehouseForm} layout="vertical">
          <Form.Item
            name="code"
            label="كود المخزن"
            rules={[{ required: true, message: 'أدخل كود المخزن' }]}
          >
            <Input placeholder="مثال: WH-001" />
          </Form.Item>
          <Form.Item
            name="name"
            label="اسم المخزن (إنجليزي)"
            rules={[{ required: true, message: 'أدخل اسم المخزن' }]}
          >
            <Input placeholder="Warehouse Name" />
          </Form.Item>
          <Form.Item
            name="name_ar"
            label="اسم المخزن (عربي)"
            rules={[{ required: true, message: 'أدخل اسم المخزن بالعربي' }]}
          >
            <Input placeholder="اسم المخزن" />
          </Form.Item>
          <Form.Item name="address" label="العنوان">
            <Input placeholder="عنوان المخزن" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Movement Modal */}
      <Modal
        title="تسجيل حركة مخزون"
        open={movementModalVisible}
        onOk={handleSaveMovement}
        onCancel={() => setMovementModalVisible(false)}
      >
        <Form form={movementForm} layout="vertical">
          <Form.Item
            name="product_id"
            label="المنتج"
            rules={[{ required: true, message: 'اختر المنتج' }]}
          >
            <Select placeholder="اختر المنتج" showSearch>
              {products.map((product) => (
                <Select.Option key={product.id} value={product.id}>
                  {product.sku} - {product.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="warehouse_id"
            label="المخزن"
            rules={[{ required: true, message: 'اختر المخزن' }]}
          >
            <Select placeholder="اختر المخزن">
              {warehouses.map((wh) => (
                <Select.Option key={wh.id} value={wh.id}>
                  {wh.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="movement_type"
            label="نوع الحركة"
            rules={[{ required: true, message: 'اختر نوع الحركة' }]}
          >
            <Select placeholder="اختر النوع">
              <Select.Option value="in">وارد (إدخال)</Select.Option>
              <Select.Option value="out">صادر (إخراج)</Select.Option>
              <Select.Option value="transfer">تحويل</Select.Option>
              <Select.Option value="adjustment">تسوية</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="quantity"
            label="الكمية"
            rules={[{ required: true, message: 'أدخل الكمية' }]}
          >
            <InputNumber style={{ width: '100%' }} min={1} placeholder="0" />
          </Form.Item>
          <Form.Item name="unit_cost" label="تكلفة الوحدة">
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              placeholder="0"
            />
          </Form.Item>
          <Form.Item name="movement_date" label="التاريخ">
            <Input type="date" />
          </Form.Item>
          <Form.Item name="notes" label="ملاحظات">
            <Input.TextArea rows={2} placeholder="ملاحظات" />
          </Form.Item>
        </Form>
      </Modal>

      {/* View Product Modal */}
      <Modal
        title={`تفاصيل المنتج: ${selectedProduct?.name}`}
        open={!!selectedProduct}
        onCancel={() => setSelectedProduct(null)}
        footer={null}
        width={700}
      >
        {selectedProduct && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="SKU">{selectedProduct.sku}</Descriptions.Item>
            <Descriptions.Item label="الباركود">{selectedProduct.barcode || '---'}</Descriptions.Item>
            <Descriptions.Item label="اسم المنتج">{selectedProduct.name}</Descriptions.Item>
            <Descriptions.Item label="الاسم (عربي)">{selectedProduct.name_ar}</Descriptions.Item>
            <Descriptions.Item label="سعر البيع">{selectedProduct.unit_price.toLocaleString('ar-EG')} ج.م</Descriptions.Item>
            <Descriptions.Item label="سعر التكلفة">{selectedProduct.cost_price.toLocaleString('ar-EG')} ج.م</Descriptions.Item>
            <Descriptions.Item label="المخزون الحالي">
              <span style={{ 
                fontWeight: 'bold',
                color: selectedProduct.current_stock <= selectedProduct.min_stock ? '#ff4d4f' : '#52c41a'
              }}>
                {selectedProduct.current_stock}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="الحد الأدنى">{selectedProduct.min_stock}</Descriptions.Item>
            <Descriptions.Item label="الوصف" span={2}>{selectedProduct.description || '---'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default InventoryPage;
