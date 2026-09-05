import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/v1`;
const apiClient = axios.create({ baseURL: API_BASE_URL, headers: { 'Content-Type': 'application/json', 'Accept-Language': 'ar' } });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use((response) => response, async (error) => {
  const originalRequest = error.config;
  if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
    originalRequest._retry = true;
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) throw new Error('No refresh token');
      const response = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken });
      const { access_token } = response.data;
      localStorage.setItem('access_token', access_token);
      originalRequest.headers.Authorization = `Bearer ${access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      return Promise.reject(refreshError);
    }
  }
  return Promise.reject(error);
});

export default apiClient;

export const authAPI = {
  login: (email: string, password: string) => apiClient.post('/auth/login', { email, password }),
  register: (userData: unknown) => apiClient.post('/auth/register', userData),
  refreshToken: (refreshToken: string) => apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
  logout: () => apiClient.post('/auth/logout'),
  getCurrentUser: () => apiClient.get('/auth/me'),
};

export const onboardingAPI = {
  start: (adminEmail?: string) => apiClient.post('/dynamic/onboarding/start', { admin_email: adminEmail }),
  status: () => apiClient.get('/dynamic/onboarding/status'),
  industries: () => apiClient.get('/dynamic/onboarding/industries'),
  completeStep: (step: string, data: Record<string, unknown>) => apiClient.post('/dynamic/onboarding/complete-step', { step, data }),
};

export const customersAPI = { getAll: (params?: unknown) => apiClient.get('/customers', { params }), getById: (id: number) => apiClient.get(`/customers/${id}`), create: (data: unknown) => apiClient.post('/customers', data), update: (id: number, data: unknown) => apiClient.put(`/customers/${id}`, data), delete: (id: number) => apiClient.delete(`/customers/${id}`) };
export const suppliersAPI = { getAll: (params?: unknown) => apiClient.get('/suppliers', { params }), getById: (id: number) => apiClient.get(`/suppliers/${id}`), create: (data: unknown) => apiClient.post('/suppliers', data), update: (id: number, data: unknown) => apiClient.put(`/suppliers/${id}`, data), delete: (id: number) => apiClient.delete(`/suppliers/${id}`) };
export const productsAPI = { getAll: (params?: unknown) => apiClient.get('/products', { params }), getById: (id: number) => apiClient.get(`/products/${id}`), create: (data: unknown) => apiClient.post('/products', data), update: (id: number, data: unknown) => apiClient.put(`/products/${id}`, data), delete: (id: number) => apiClient.delete(`/products/${id}`) };
export const ordersAPI = { getAll: (params?: unknown) => apiClient.get('/orders', { params }), getById: (id: number) => apiClient.get(`/orders/${id}`), create: (data: unknown) => apiClient.post('/orders', data), update: (id: number, data: unknown) => apiClient.put(`/orders/${id}`, data), delete: (id: number) => apiClient.delete(`/orders/${id}`) };
export const invoicesAPI = { getAll: (params?: unknown) => apiClient.get('/invoices', { params }), getById: (id: number) => apiClient.get(`/invoices/${id}`), create: (data: unknown) => apiClient.post('/invoices', data), update: (id: number, data: unknown) => apiClient.put(`/invoices/${id}`, data), delete: (id: number) => apiClient.delete(`/invoices/${id}`) };
export const reportsAPI = { getDashboard: () => apiClient.get('/reports/dashboard'), getSalesReport: (params?: unknown) => apiClient.get('/reports/sales', { params }), getInventoryReport: (params?: unknown) => apiClient.get('/reports/inventory', { params }), getFinancialReport: (params?: unknown) => apiClient.get('/reports/financial', { params }) };
