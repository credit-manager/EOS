import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/v1`;
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json', 'Accept-Language': 'ar' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('eos_tenant_id');
      localStorage.removeItem('eos_user');
      window.dispatchEvent(new Event('eos:auth-expired'));
    }
    return Promise.reject(error);
  },
);

export default apiClient;

export const authAPI = {
  login: (email: string, password: string) => apiClient.post('/auth/login', { email, password }),
  register: (userData: unknown) => apiClient.post('/auth/register', userData),
  logout: () => apiClient.post('/auth/logout'),
  getCurrentUser: () => apiClient.get('/auth/me'),
};

export const onboardingAPI = {
  start: (adminEmail?: string) => apiClient.post('/dynamic/onboarding/start', { admin_email: adminEmail }),
  status: () => apiClient.get('/dynamic/onboarding/status'),
  industries: () => apiClient.get('/dynamic/onboarding/industries'),
  modules: (category?: string) => apiClient.get('/dynamic/onboarding/modules', { params: category ? { category } : undefined }),
  completeStep: (step: string, data: Record<string, unknown>) => apiClient.post('/dynamic/onboarding/complete-step', { step, data }),
};

export const customersAPI = {
  getAll: (params?: unknown) => apiClient.get('/sales/customers', { params }),
  getById: (id: number) => apiClient.get(`/sales/customers/${id}`),
  create: (data: unknown) => apiClient.post('/sales/customers', data),
  update: (id: number, data: unknown) => apiClient.put(`/sales/customers/${id}`, data),
  delete: (id: number) => apiClient.delete(`/sales/customers/${id}`),
};

export const suppliersAPI = {
  getAll: (params?: unknown) => apiClient.get('/inventory/suppliers', { params }),
  getById: (id: number) => apiClient.get(`/inventory/suppliers/${id}`),
  create: (data: unknown) => apiClient.post('/inventory/suppliers', data),
  update: (id: number, data: unknown) => apiClient.put(`/inventory/suppliers/${id}`, data),
  delete: (id: number) => apiClient.delete(`/inventory/suppliers/${id}`),
};

export const productsAPI = {
  getAll: (params?: unknown) => apiClient.get('/inventory/products', { params }),
  getById: (id: number) => apiClient.get(`/inventory/products/${id}`),
  create: (data: unknown) => apiClient.post('/inventory/products', data),
  update: (id: number, data: unknown) => apiClient.put(`/inventory/products/${id}`, data),
  delete: (id: number) => apiClient.delete(`/inventory/products/${id}`),
};

// Orders and invoices are intentionally not wired to a guessed endpoint.
// The backend implements them per industry template. See
// docs/FRONTEND_API_CONTRACT_MISMATCHES.md for the canonical integration plan.
const unavailableAPI = (resource: string) => () => Promise.reject(
  new Error(`${resource} API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md`),
);

export const ordersAPI = {
  getAll: unavailableAPI('orders'),
  getById: (_id: number) => Promise.reject(new Error('orders API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
  create: (_data: unknown) => Promise.reject(new Error('orders API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
  update: (_id: number, _data: unknown) => Promise.reject(new Error('orders API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
  delete: (_id: number) => Promise.reject(new Error('orders API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
};

export const invoicesAPI = {
  getAll: unavailableAPI('invoices'),
  getById: (_id: number) => Promise.reject(new Error('invoices API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
  create: (_data: unknown) => Promise.reject(new Error('invoices API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
  update: (_id: number, _data: unknown) => Promise.reject(new Error('invoices API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
  delete: (_id: number) => Promise.reject(new Error('invoices API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md')),
};

export const reportsAPI = {
  profitAndLoss: (params?: { start_date?: string; end_date?: string }) => apiClient.get('/reports/profit-and-loss', { params }),
  balanceSheet: () => apiClient.get('/reports/balance-sheet'),
  cashFlow: (days = 30) => apiClient.get('/reports/cash-flow', { params: { days } }),
  sales: (params?: { start_date?: string; end_date?: string }) => apiClient.get('/reports/sales', { params }),
  inventory: () => apiClient.get('/reports/inventory'),
  customerAging: () => apiClient.get('/reports/customer-aging'),
  industry: (industry: string) => apiClient.get(`/reports/industry/${encodeURIComponent(industry)}`),
  export: (report_type: string, format = 'json') => apiClient.post('/reports/export', { report_type, format }),
};
