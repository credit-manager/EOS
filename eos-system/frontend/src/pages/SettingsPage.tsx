import React from 'react';
import { Card, Typography, Form, Input, Switch, Button, Tabs } from 'antd';
import { SaveOutlined } from '@ant-design/icons';

const { Title } = Typography;
const { TabPane } = Tabs;

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm();

  const onFinish = (values: any) => {
    console.log('Settings saved:', values);
  };

  return (
    <div>
      <Title level={4}>الإعدادات</Title>
      
      <Tabs defaultActiveKey="general">
        <TabPane tab="إعدادات عامة" key="general">
          <Card>
            <Form
              form={form}
              layout="vertical"
              onFinish={onFinish}
              initialValues={{
                companyName: 'شركتي',
                companyNameAr: 'شركتي',
                currency: 'EGP',
                timezone: 'Africa/Cairo',
              }}
            >
              <Form.Item label="اسم الشركة" name="companyName">
                <Input />
              </Form.Item>
              
              <Form.Item label="اسم الشركة (عربي)" name="companyNameAr">
                <Input />
              </Form.Item>
              
              <Form.Item label="العملة" name="currency">
                <Input disabled />
              </Form.Item>
              
              <Form.Item label="المنطقة الزمنية" name="timezone">
                <Input disabled />
              </Form.Item>
              
              <Form.Item>
                <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                  حفظ التغييرات
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
        
        <TabPane tab="الفريق" key="team">
          <Card>
            <p>إدارة أعضاء الفريق - قيد التطوير</p>
          </Card>
        </TabPane>
        
        <TabPane tab="الفواتير الإلكترونية" key="eta">
          <Card>
            <Form layout="vertical">
              <Form.Item label="رقم التسجيل الضريبي">
                <Input placeholder="أدخل رقم التسجيل الضريبي" />
              </Form.Item>
              
              <Form.Item label="رقم التأمينات الاجتماعية">
                <Input placeholder="أدخل رقم التأمينات" />
              </Form.Item>
              
              <Form.Item label="تفعيل الفوترة الإلكترونية">
                <Switch defaultChecked />
              </Form.Item>
              
              <Form.Item>
                <Button type="primary" icon={<SaveOutlined />}>
                  حفظ
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
        
        <TabPane tab="الأمان" key="security">
          <Card>
            <Form layout="vertical">
              <Form.Item label="المصادقة الثنائية">
                <Switch />
              </Form.Item>
              
              <Form.Item label="مهلة انتهاء الجلسة (دقيقة)">
                <Input type="number" defaultValue={30} />
              </Form.Item>
              
              <Form.Item>
                <Button type="primary" icon={<SaveOutlined />}>
                  حفظ
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default SettingsPage;
