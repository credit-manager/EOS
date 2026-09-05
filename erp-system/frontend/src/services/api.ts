import axios, { AxiosError } from 'axios';

const runtimeOrigin = typeof window !== 'undefined' ? window.location.origin : '';
const API_BASE_URL = import.meta.env.VITE_API_URL || `${runtimeOrigin}/api/v1`;
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json', 'Accept-Language': 'ar' },
});

const clearLocalSession = () => {
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('eos_tenant_id');
    localStorage.removeItem('eos_user');
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('eos:auth-expired'));
  }
};

apiClient.interceptors.request.use((config) => {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('access_token') : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const data = response.data?.data;
    if (typeof localStorage !== 'undefined') {
      if (data?.access_token) localStorage.setItem('access_token', data.access_token);
      if (data?.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);
    }
    return response;
  },
  async (error: AxiosError) => {
    const original = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
    const url = original?.url || '';
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/register');
    if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint) {
      const refreshToken = typeof localStorage !== 'undefined' ? localStorage.getItem('refresh_token') : null;
      if (refreshToken) {
        original._retry = true;
        try {
          const refreshResponse = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
          const refreshed = refreshResponse.data?.data;
          if (refreshed?.access_token && refreshed?.refresh_token) {
            localStorage.setItem('access_token', refreshed.access_token);
            localStorage.setItem('refresh_token', refreshed.refresh_token);
            original.headers = original.headers || {};
            original.headers.Authorization = `Bearer ${refreshed.access_token}`;
            return apiClient.request(original);
          }
        } catch {
          clearLocalSession();
        }
      } else {
        clearLocalSession();
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;

export const authAPI = {
  login: (email: string, password: string) => apiClient.post('/auth/login', { email, password }),
  register: (userData: unknown) => apiClient.post('/auth/register', userData),
  logout: async () => {
    const refreshToken = typeof localStorage !== 'undefined' ? localStorage.getItem('refresh_token') : null;
    try {
      if (refreshToken) await apiClient.post('/auth/logout', { refresh_token: refreshToken });
    } finally {
      clearLocalSession();
    }
    return { data: { status: 'success', data: { message: 'Logged out' } } };
  },
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
  getById: (id: string | number) => apiClient.get(`/sales/customers/${id}`),
  create: (data: unknown) => apiClient.post('/sales/customers', data),
  update: (id: string | number, data: unknown) => apiClient.put(`/sales/customers/${id}`, data),
  delete: (id: string | number) => apiClient.delete(`/sales/customers/${id}`),
};

export const suppliersAPI = {
  getAll: (params?: unknown) => apiClient.get('/inventory/suppliers', { params }),
  getById: (id: string | number) => apiClient.get(`/inventory/suppliers/${id}`),
  create: (data: unknown) => apiClient.post('/inventory/suppliers', data),
  update: (id: string | number, data: unknown) => apiClient.put(`/inventory/suppliers/${id}`, data),
  delete: (id: string | number) => apiClient.delete(`/inventory/suppliers/${id}`),
};

export const productsAPI = {
  getAll: (params?: unknown) => apiClient.get('/inventory/products', { params }),
  getById: (id: string | number) => apiClient.get(`/inventory/products/${id}`),
  create: (data: unknown) => apiClient.post('/inventory/products', data),
  update: (id: string | number, data: unknown) => apiClient.put(`/inventory/products/${id}`, data),
  delete: (id: string | number) => apiClient.delete(`/inventory/products/${id}`),
};

const unavailableAPI = (resource: string) => () => Promise.reject(
  new Error(`${resource} API is not wired to a generic backend endpoint yet; see docs/FRONTEND_API_CONTRACT_MISMATCHES.md`),
);

export const ordersAPI = {
  getAll: unavailableAPI('orders'),
  getById: (_id: string | number) => unavailableAPI('orders')(),
  create: (_data: unknown) => unavailableAPI('orders')(),
  update: (_id: string | number, _data: unknown) => unavailableAPI('orders')(),
  delete: (_id: string | number) => unavailableAPI('orders')(),
};

export const invoicesAPI = {
  getAll: unavailableAPI('invoices'),
  getById: (_id: string | number) => unavailableAPI('invoices')(),
  create: (_data: unknown) => unavailableAPI('invoices')(),
  update: (_id: string | number, _data: unknown) => unavailableAPI('invoices')(),
  delete: (_id: string | number) => unavailableAPI('invoices')(),
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
