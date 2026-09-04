import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Badge, Drawer } from 'antd'
import {
  DashboardOutlined,
  AppstoreOutlined,
  BuildOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  SettingOutlined,
  BellOutlined,
  GlobalOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import './Layout.css'

const { Header, Sider, Content } = AntLayout

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'dashboard' },
  { key: '/industries', icon: <AppstoreOutlined />, label: 'industries' },
  { key: '/builder', icon: <BuildOutlined />, label: 'builder' },
  { key: '/entities', icon: <DatabaseOutlined />, label: 'entities' },
  { key: '/reports', icon: <FileTextOutlined />, label: 'reports' },
  { key: '/settings', icon: <SettingOutlined />, label: 'settings' },
]

function clearAuthState() {
  localStorage.removeItem('eos_token')
  localStorage.removeItem('eos_tenant_id')
  localStorage.removeItem('eos_user')
}

function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const [languageDrawerOpen, setLanguageDrawerOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { t, i18n } = useTranslation()

  const handleMenuClick = ({ key }) => {
    navigate(key)
  }

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng)
    localStorage.setItem('eos_language', lng)
    setLanguageDrawerOpen(false)
  }

  const userMenu = {
    items: [
      {
        key: 'profile',
        icon: <UserOutlined />,
        label: t('profile'),
        onClick: () => navigate('/settings'),
      },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: t('logout'),
        danger: true,
        onClick: () => {
          clearAuthState()
          navigate('/login', { replace: true })
        },
      },
    ],
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
        <div className="logo">
          <h2>{collapsed ? 'EOS' : 'EOS ERP'}</h2>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems.map(item => ({
            ...item,
            label: t(item.label),
          }))}
          onClick={handleMenuClick}
        />
      </Sider>
      <AntLayout>
        <Header className="header">
          <div className="header-left">
            {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
              className: 'trigger',
              onClick: () => setCollapsed(!collapsed),
            })}
          </div>
          <div className="header-right">
            <Badge count={3} size="small">
              <BellOutlined className="header-icon" />
            </Badge>
            <GlobalOutlined
              className="header-icon"
              onClick={() => setLanguageDrawerOpen(true)}
              style={{ cursor: 'pointer' }}
            />
            <Dropdown menu={userMenu} placement="bottomRight" arrow>
              <Avatar
                icon={<UserOutlined />}
                size="large"
                style={{ backgroundColor: '#1890ff', cursor: 'pointer' }}
              />
            </Dropdown>
          </div>
        </Header>
        <Content className="content">
          <Outlet />
        </Content>
      </AntLayout>

      <Drawer
        title={t('language')}
        placement="right"
        onClose={() => setLanguageDrawerOpen(false)}
        open={languageDrawerOpen}
      >
        <div className="language-options">
          <div className={`language-option ${i18n.language === 'ar' ? 'active' : ''}`} onClick={() => changeLanguage('ar')}>
            🇸🇦 العربية
          </div>
          <div className={`language-option ${i18n.language === 'en' ? 'active' : ''}`} onClick={() => changeLanguage('en')}>
            🇬🇧 English
          </div>
          <div className={`language-option ${i18n.language === 'fr' ? 'active' : ''}`} onClick={() => changeLanguage('fr')}>
            🇫🇷 Français
          </div>
          <div className={`language-option ${i18n.language === 'de' ? 'active' : ''}`} onClick={() => changeLanguage('de')}>
            🇩🇪 Deutsch
          </div>
          <div className={`language-option ${i18n.language === 'es' ? 'active' : ''}`} onClick={() => changeLanguage('es')}>
            🇪🇸 Español
          </div>
          <div className={`language-option ${i18n.language === 'zh' ? 'active' : ''}`} onClick={() => changeLanguage('zh')}>
            🇨🇳 中文
          </div>
        </div>
      </Drawer>
    </AntLayout>
  )
}

export default Layout
