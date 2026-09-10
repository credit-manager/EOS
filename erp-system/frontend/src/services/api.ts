import axios, { AxiosError } from 'axios';

const runtimeOrigin = typeof window !== 'undefined' ? window.location.origin : '';
const API_BASE_URL = import.meta.env.VITE_API_URL || `${runtimeOrigin}/api/v1`;
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json', 'Accept-Language': 'ar' },
});

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

const setAccessToken = (token: unknown) => {
  accessToken = typeof token === 'string' && token ? token : null;
};

const clearLocalSession = () => {
  setAccessToken(null);
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('eos_tenant_id');
    localStorage.removeItem('eos_company_id');
    localStorage.removeItem('eos_user');
  }
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('eos:auth-expired'));
};

const refreshAccessToken = async (): Promise<string | null> => {
  if (refreshPromise) return refreshPromise;
  refreshPromise = apiClient.post('/auth/refresh', {}).then((response) => {
    const token = response.data?.data?.access_token;
    setAccessToken(token);
    return accessToken;
  }).catch(() => {
    clearLocalSession();
    return null;
  }).finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
};

apiClient.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const data = response.data?.data;
    setAccessToken(data?.access_token);
    if (typeof localStorage !== 'undefined') {
      if (data?.user?.tenant_id) localStorage.setItem('eos_tenant_id', String(data.user.tenant_id));
      if (data?.user?.company_id) localStorage.setItem('eos_company_id', String(data.user.company_id));
    }
    return response;
  },
  async (error: AxiosError) => {
    const original = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
    const url = original?.url || '';
    const isAuthEndpoint = ['/auth/login', '/auth/refresh', '/auth/register', '/auth/verify-email', '/auth/2fa/verify', '/auth/2fa/verify-recovery'].some((p) => url.includes(p));
    if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken) {
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${refreshedToken}`;
        return apiClient.request(original);
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;

export const authAPI = {
  login: (email: string, password: string) => apiClient.post('/auth/login', { email, password }),
  register: (userData: unknown) => apiClient.post('/auth/register', userData),
  verifyEmail: (token: string) => apiClient.post('/auth/verify-email', { token }),
  verify2FA: (code: string) => apiClient.post('/auth/2fa/verify', { code }),
  verifyRecoveryCode: (code: string) => apiClient.post('/auth/2fa/verify-recovery', { code }),
  logout: async () => {
    try { await apiClient.post('/auth/logout', {}); }
    finally { clearLocalSession(); }
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

const getCompanyId = () => {
  const companyId = typeof localStorage !== 'undefined' ? localStorage.getItem('eos_company_id') : null;
  if (!companyId) throw new Error('EOS company context is not available; complete company onboarding first.');
  return companyId;
};

export const ordersAPI = {
  getAll: (companyId = getCompanyId(), params?: { status?: string }) => apiClient.get(`/dynamic/companies/${companyId}/sales-orders`, { params }),
  getById: (id: string | number) => apiClient.get(`/dynamic/sales-orders/${id}`),
  create: (data: Record<string, unknown>, companyId = getCompanyId()) => apiClient.post(`/dynamic/companies/${companyId}/sales-orders`, data),
  update: (_id: string | number, _data: unknown) => Promise.reject(new Error('Sales order updates require an explicit workflow endpoint.')),
  delete: (_id: string | number) => Promise.reject(new Error('Sales order deletion is disabled to preserve financial auditability.')),
};

export const invoicesAPI = {
  getAll: (companyId = getCompanyId(), params?: { status?: string }) => apiClient.get(`/dynamic/companies/${companyId}/invoices`, { params }),
  getById: (id: string | number) => apiClient.get(`/dynamic/invoices/${id}`),
  create: (data: Record<string, unknown>, companyId = getCompanyId()) => apiClient.post(`/dynamic/companies/${companyId}/invoices`, data),
  issue: (id: string | number) => apiClient.post(`/dynamic/invoices/${id}/issue`),
  recordPayment: (id: string | number, amount: number, paymentDate: string) => apiClient.post(`/dynamic/invoices/${id}/payments`, { amount, payment_date: paymentDate }),
  update: (_id: string | number, _data: unknown) => Promise.reject(new Error('Issued invoice updates are disabled; use controlled credit/debit workflows.')),
  delete: (_id: string | number) => Promise.reject(new Error('Issued invoice deletion is disabled to preserve financial auditability.')),
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
