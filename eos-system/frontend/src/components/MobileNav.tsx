/**
 * EOS System — Mobile Bottom Navigation (P66)
 * Thumb-reachable primary navigation for phones (RTL-aware).
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  BarChartOutlined,
  ShoppingCartOutlined,
  ProjectOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';

export const MOBILE_NAV_ITEMS = [
  { key: '/dashboard', label: 'الرئيسية', icon: <DashboardOutlined /> },
  { key: '/analytics', label: 'تحليلات', icon: <BarChartOutlined /> },
  { key: '/sales', label: 'المبيعات', icon: <ShoppingCartOutlined /> },
  { key: '/projects', label: 'المشاريع', icon: <ProjectOutlined /> },
];

interface MobileNavProps {
  onMore?: () => void;
}

const MobileNav: React.FC<MobileNavProps> = ({ onMore }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (key: string) =>
    location.pathname === key || location.pathname.startsWith(key + '/');

  return (
    <nav className="eos-mobile-nav" aria-label="التنقل الرئيسي">
      {MOBILE_NAV_ITEMS.map((item) => (
        <button
          key={item.key}
          className={`eos-mobile-nav-item ${isActive(item.key) ? 'active' : ''}`}
          onClick={() => navigate(item.key)}
          aria-current={isActive(item.key) ? 'page' : undefined}
        >
          <span className="eos-mobile-nav-icon">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
      <button
        className={`eos-mobile-nav-item ${onMore ? '' : ''}`}
        onClick={onMore}
        aria-label="المزيد"
      >
        <span className="eos-mobile-nav-icon">
          <AppstoreOutlined />
        </span>
        <span>المزيد</span>
      </button>
    </nav>
  );
};

export default MobileNav;
