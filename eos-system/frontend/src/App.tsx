import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import MainLayout from './layouts/MainLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import AccountingPage from './pages/AccountingPage';
import InventoryPage from './pages/InventoryPage';
import HRPage from './pages/HRPage';
import SalesPage from './pages/SalesPage';
import ProjectsPage from './pages/ProjectsPage';
import AIPage from './pages/AIPage';
import SettingsPage from './pages/SettingsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import BrandingPage from './pages/BrandingPage';
import ControlCenterPage from './pages/ControlCenterPage';
import ConstructionPage from './pages/ConstructionPage';
import TradingPage from './pages/TradingPage';
import RetailPage from './pages/RetailPage';
import RestaurantPage from './pages/RestaurantPage';
import ManufacturingPage from './pages/ManufacturingPage';
import ServicesPage from './pages/ServicesPage';

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Protected Routes */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <MainLayout>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/accounting/*" element={<AccountingPage />} />
                  <Route path="/inventory/*" element={<InventoryPage />} />
                  <Route path="/hr/*" element={<HRPage />} />
                  <Route path="/sales/*" element={<SalesPage />} />
                  <Route path="/projects/*" element={<ProjectsPage />} />
                  <Route path="/analytics/*" element={<AnalyticsPage />} />
                  <Route path="/ai/*" element={<AIPage />} />
                  <Route path="/branding" element={<BrandingPage />} />
                  <Route path="/control/*" element={<ControlCenterPage />} />
                  <Route path="/construction" element={<ConstructionPage />} />
                  <Route path="/trading" element={<TradingPage />} />
                  <Route path="/retail" element={<RetailPage />} />
                  <Route path="/restaurant" element={<RestaurantPage />} />
                  <Route path="/manufacturing" element={<ManufacturingPage />} />
                  <Route path="/services" element={<ServicesPage />} />
                  <Route path="/settings/*" element={<SettingsPage />} />
                </Routes>
              </MainLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
};

export default App;
