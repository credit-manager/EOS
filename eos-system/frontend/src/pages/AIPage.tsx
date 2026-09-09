import React from 'react';
import { Card, Typography, Input, Button, Space, List, Avatar } from 'antd';
import { RobotOutlined, SendOutlined, UserOutlined } from '@ant-design/icons';

const { Title } = Typography;
const { TextArea } = Input;

const AIPage: React.FC = () => {
  // Mock chat messages
  const messages = [
    {
      id: 1,
      role: 'assistant',
      content: 'مرحباً! أنا مساعدك الذكي في نظام EOS. كيف يمكنني مساعدتك اليوم؟',
    },
    {
      id: 2,
      role: 'user',
      content: 'كم إجمالي مبيعات الشهر؟',
    },
    {
      id: 3,
      role: 'assistant',
      content: 'إجمالي مبيعات الشهر الحالي هو 156,789 ج.م، وهو أعلى بـ 12.5% من الشهر الماضي. هل تريد رؤية تفاصيل أكثر؟',
    },
  ];

  return (
    <div style={{ height: 'calc(100vh - 160px)', display: 'flex', flexDirection: 'column' }}>
      <Title level={4}>
        <RobotOutlined /> المساعد الذكي (AI Copilot)
      </Title>
      
      {/* Chat Area */}
      <Card 
        style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}
        bodyStyle={{ padding: 16 }}
      >
        <List
          dataSource={messages}
          renderItem={(item) => (
            <List.Item style={{ border: 'none', padding: '8px 0' }}>
              <Space
                style={{
                  width: '100%',
                  justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                {item.role === 'assistant' && (
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                )}
                <div
                  style={{
                    maxWidth: '70%',
                    padding: '12px 16px',
                    borderRadius: 12,
                    backgroundColor: item.role === 'user' ? '#1890ff' : '#f0f0f0',
                    color: item.role === 'user' ? '#fff' : '#000',
                  }}
                >
                  {item.content}
                </div>
                {item.role === 'user' && (
                  <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#87d068' }} />
                )}
              </Space>
            </List.Item>
          )}
        />
      </Card>
      
      {/* Input Area */}
      <Card>
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            placeholder="اكتب سؤالك هنا... (مثال: كم مبيعات اليوم؟)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
          />
          <Button type="primary" icon={<SendOutlined />} style={{ height: 'auto' }}>
            إرسال
          </Button>
        </Space.Compact>
        
        {/* Quick Actions */}
        <Space wrap style={{ marginTop: 12 }}>
          <Button size="small">ملخص المبيعات</Button>
          <Button size="small">فحص المخزون</Button>
          <Button size="small">تقرير أرباح</Button>
          <Button size="small">تنبيهات</Button>
        </Space>
      </Card>
    </div>
  );
};

export default AIPage;
