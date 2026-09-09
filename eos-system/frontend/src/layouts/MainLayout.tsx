import React, { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, Space, Typography, Grid, Drawer, Badge, Input, Tooltip } from 'antd';
import {
  DashboardOutlined,
  AccountBookOutlined,
  ShopOutlined,
  TeamOutlined,
  ShoppingCartOutlined,
  ProjectOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BarChartOutlined,
  MenuOutlined,
  DisconnectOutlined,
  SearchOutlined,
  BellOutlined,
  CrownOutlined,
  ImportOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CoffeeOutlined,
  ControlOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useBrandingStore } from '../stores/brandingStore';
import { useTenantContext, INDUSTRY_MODULES } from '../stores/tenantContext';
import { getQueueSize } from '../services/offlineQueue';
import OfflineBanner from '../components/OfflineBanner';
import MobileNav from '../components/MobileNav';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

const ICON_MAP: Record<string, React.ReactNode> = {
  HomeOutlined: <DashboardOutlined />,
  ProjectOutlined: <ProjectOutlined />,
  ShoppingCartOutlined: <ShoppingCartOutlined />,
  ShopOutlined: <ShopOutlined />,
  TeamOutlined: <TeamOutlined />,
  AccountBookOutlined: <AccountBookOutlined />,
  BarChartOutlined: <BarChartOutlined />,
  FileTextOutlined: <FileTextOutlined />,
  ToolOutlined: <ShopOutlined />,
  CheckCircleOutlined: <CheckCircleOutlined />,
  CoffeeOutlined: <CoffeeOutlined />,
  SettingOutlined: <ControlOutlined />,
  ImportOutlined: <ImportOutlined />,
};

const FALLBACK_MENU = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'لوحة التحكم' },
  { key: '/analytics', icon: <BarChartOutlined />, label: 'التحليلات' },
  { key: '/sales', icon: <ShoppingCartOutlined />, label: 'المبيعات' },
  { key: '/inventory', icon: <ShopOutlined />, label: 'المخزون' },
  { key: '/accounting', icon: <AccountBookOutlined />, label: 'المحاسبة' },
  { key: '/projects', icon: <ProjectOutlined />, label: 'المشاريع' },
  { key: '/hr', icon: <TeamOutlined />, label: 'الموارد البشرية' },
];

const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const [pendingCount, setPendingCount] = useState<number>(() => getQueueSize());
  React.useEffect(() => {
    const onChange = (e: Event) =>
      setPendingCount((e as CustomEvent).detail?.size ?? 0);
    window.addEventListener('eos-offline-queue-changed', onChange);
    return () => window.removeEventListener('eos-offline-queue-changed', onChange);
  }, []);

  const { user, logout } = useAuthStore();
  const branding = useBrandingStore((s) => s.branding);
  const { industry, companyName, menuItems: apiMenuItems, setTenant } = useTenantContext();
  const showPoweredBy = branding?.show_powered_by !== false;

  // Sync tenant context from localStorage on mount
  React.useEffect(() => {
    const tid = localStorage.getItem('tenant_id');
    const ind = localStorage.getItem('tenant_industry');
    const cn = localStorage.getItem('tenant_company_name');
    const mods = localStorage.getItem('tenant_modules');
    if (tid && ind) {
      setTenant({
        tenantId: tid,
        industry: ind,
        companyName: cn || undefined,
        modules: mods ? JSON.parse(mods) : [],
      });
    }
  }, []);

  // Build dynamic menu based on industry — API menu preferred, static fallback
  const menuItems = React.useMemo(() => {
    // Prefer API-provided menu from Industry Framework
    if (apiMenuItems && apiMenuItems.length > 0) {
      const items = apiMenuItems.map((mod: any) => ({
        key: mod.path,
        icon: ICON_MAP[mod.icon] || <DashboardOutlined />,
        label: mod.labelAr || mod.label,
      }));
      items.push(
        { key: '/settings', icon: <SettingOutlined />, label: 'الإعدادات' } as any,
        { key: '/control', icon: <CrownOutlined />, label: 'EOS Control' } as any,
      );
      return items;
    }

    // Fallback to static INDUSTRY_MODULES
    const industryModules = INDUSTRY_MODULES[industry || ''];
    if (!industryModules) return FALLBACK_MENU;

    const items = industryModules.map((mod) => ({
      key: mod.path,
      icon: ICON_MAP[mod.icon] || <DashboardOutlined />,
      label: mod.labelAr,
    }));

    items.push(
      { key: '/settings', icon: <SettingOutlined />, label: 'الإعدادات' } as any,
      { key: '/control', icon: <CrownOutlined />, label: 'EOS Control' } as any,
    );

    return items;
  }, [industry, apiMenuItems]);

  const activeKey =
    menuItems.find(
      (item: any) =>
        !item.type &&
        (location.pathname === item.key ||
         location.pathname.startsWith(item.key + '/'))
    )?.key || '/dashboard';

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'الملف الشخصي',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'تسجيل الخروج',
      danger: true,
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
    setDrawerOpen(false);
  };

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout();
      navigate('/login');
    }
  };

  const brandBlock = (
    <div
      style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed && !drawerOpen ? 'center' : 'flex-start',
        padding: collapsed && !drawerOpen ? '0' : '0 20px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        flexShrink: 0,
      }}
    >
      <Space align="center" size={10}>
        {branding?.logo_url && (
          <img
            src={branding.logo_url}
            alt="logo"
            style={{
              height: collapsed && !drawerOpen ? 28 : 32,
              maxWidth: 40,
              objectFit: 'contain',
              borderRadius: 6,
            }}
          />
        )}
        {(collapsed && !drawerOpen) || (isMobile && !drawerOpen) ? null : (
          <div>
            <Text
              style={{
                color: '#fff',
                fontSize: 16,
                fontWeight: 'bold',
                display: 'block',
                lineHeight: 1.2,
              }}
            >
              {companyName || branding?.system_name_en || 'EOS'}
            </Text>
            {industry && (
              <Text
                style={{
                  color: 'rgba(255,255,255,0.45)',
                  fontSize: 11,
                  display: 'block',
                  lineHeight: 1.2,
                  marginTop: 2,
                }}
              >
                {industry.charAt(0).toUpperCase() + industry.slice(1)} ERP
              </Text>
            )}
          </div>
        )}
      </Space>
    </div>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* ── Desktop Sidebar ── */}
      {!isMobile && (
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          width={240}
          collapsedWidth={72}
          style={{
            overflow: 'auto',
            height: '100vh',
            position: 'fixed',
            right: 0,
            top: 0,
            bottom: 0,
            background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
            zIndex: 100,
            borderLeft: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          {brandBlock}

          <div style={{ padding: '12px 8px', flex: 1 }}>
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[activeKey]}
              items={menuItems}
              onClick={handleMenuClick}
              style={{
                background: 'transparent',
                borderInlineStart: 0,
              }}
            />
          </div>

          {/* User info at bottom */}
          {!collapsed && (
            <div style={{
              position: 'absolute', bottom: 0, left: 0, right: 0,
              padding: '12px 16px',
              borderTop: '1px solid rgba(255,255,255,0.06)',
              background: 'rgba(0,0,0,0.2)',
            }}>
              <Space size={10}>
                <Avatar
                  size={36}
                  icon={<UserOutlined />}
                  style={{
                    background: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text style={{ color: '#fff', fontSize: 13, display: 'block', fontWeight: 500 }}>
                    {user?.firstName} {user?.lastName}
                  </Text>
                  <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 11 }}>
                    مدير النظام
                  </Text>
                </div>
              </Space>
            </div>
          )}
        </Sider>
      )}

      {/* ── Mobile Drawer ── */}
      <Drawer
        title={null}
        placement="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={280}
        styles={{
          body: { padding: 0, background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)' },
          header: { display: 'none' },
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {brandBlock}
          <div style={{ flex: 1, padding: '12px 8px' }}>
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[activeKey]}
              items={menuItems}
              onClick={handleMenuClick}
              style={{ background: 'transparent', borderInlineStart: 0 }}
            />
          </div>
        </div>
      </Drawer>

      <Layout
        style={{
          marginRight: isMobile ? 0 : collapsed ? 72 : 240,
          transition: 'margin-right 0.3s cubic-bezier(0.2, 0, 0, 1)',
        }}
      >
        {/* ── Header ── */}
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            position: 'sticky',
            top: 0,
            zIndex: 99,
            height: 64,
            lineHeight: '64px',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Space size={16}>
            {isMobile ? (
              <MenuOutlined
                onClick={() => setDrawerOpen(true)}
                style={{ fontSize: 20, cursor: 'pointer', color: '#374151' }}
              />
            ) : (
              <Tooltip title={collapsed ? 'توسيع القائمة' : 'طي القائمة'}>
                {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
                  onClick: () => setCollapsed(!collapsed),
                  style: { fontSize: 18, cursor: 'pointer', color: '#374151' },
                })}
              </Tooltip>
            )}

            {/* Search bar */}
            {!isMobile && (
              <Input
                prefix={<SearchOutlined style={{ color: '#9ca3af' }} />}
                placeholder="بحث سريع..."
                style={{
                  width: 280, borderRadius: 10, background: '#f9fafb',
                  border: '1px solid #e5e7eb',
                }}
                variant="borderless"
              />
            )}
          </Space>

          <Space size={16}>
            {pendingCount > 0 && (
              <Badge count={pendingCount} size="small">
                <DisconnectOutlined style={{ fontSize: 18, color: '#f59e0b' }} />
              </Badge>
            )}

            <Tooltip title="الإشعارات">
              <Badge count={0} size="small">
                <BellOutlined style={{ fontSize: 18, color: '#6b7280', cursor: 'pointer' }} />
              </Badge>
            </Tooltip>

            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }}
              placement="bottomLeft"
            >
              <Space style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: 10 }}>
                <Avatar
                  size={36}
                  icon={<UserOutlined />}
                  style={{
                    background: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
                  }}
                />
                {!isMobile && (
                  <div>
                    <Text style={{ fontSize: 13, fontWeight: 500, display: 'block', lineHeight: 1.2 }}>
                      {user?.firstName} {user?.lastName}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      مدير النظام
                    </Text>
                  </div>
                )}
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* ── Content ── */}
        <Content
          style={{
            margin: isMobile ? 12 : 24,
            padding: isMobile ? 16 : 32,
            background: '#f8fafc',
            minHeight: 'calc(100vh - 64px)',
            borderRadius: isMobile ? 0 : 16,
          }}
        >
          <OfflineBanner />
          {children}
          {showPoweredBy && (
            <div style={{ textAlign: 'center', padding: '16px 0 8px', opacity: 0.4 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>Powered by EOS</Text>
            </div>
          )}
        </Content>

        {isMobile && <MobileNav onMore={() => setDrawerOpen(true)} />}
      </Layout>
    </Layout>
  );
};

export default MainLayout;
