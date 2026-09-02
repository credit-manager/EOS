import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// إنشاء مثيل Axios
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept-Language': 'ar',
  },
});

// اعتراض الطلبات لإضافة رمز المصادقة
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// اعتراض الاستجابات للتعامل مع الأخطاء
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // إذا كان الخطأ 401 وحاولنا بالفعل إعادة_refresh_الرمز
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token } = response.data;
        localStorage.setItem('access_token', access_token);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // فشل تحديث الرمز، تسجيل الخروج
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// دوال مساعدة للمصادقة
export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),
  
  register: (userData: any) =>
    apiClient.post('/auth/register', userData),
  
  refreshToken: (refreshToken: string) =>
    apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
  
  logout: () =>
    apiClient.post('/auth/logout'),
  
  getCurrentUser: () =>
    apiClient.get('/auth/me'),
};

// دوال مساعدة للعملاء
export const customersAPI = {
  getAll: (params?: any) =>
    apiClient.get('/customers', { params }),
  
  getById: (id: number) =>
    apiClient.get(`/customers/${id}`),
  
  create: (data: any) =>
    apiClient.post('/customers', data),
  
  update: (id: number, data: any) =>
    apiClient.put(`/customers/${id}`, data),
  
  delete: (id: number) =>
    apiClient.delete(`/customers/${id}`),
};

// دوال مساعدة للموردين
export const suppliersAPI = {
  getAll: (params?: any) =>
    apiClient.get('/suppliers', { params }),
  
  getById: (id: number) =>
    apiClient.get(`/suppliers/${id}`),
  
  create: (data: any) =>
    apiClient.post('/suppliers', data),
  
  update: (id: number, data: any) =>
    apiClient.put(`/suppliers/${id}`, data),
  
  delete: (id: number) =>
    apiClient.delete(`/suppliers/${id}`),
};

// دوال مساعدة للمنتجات
export const productsAPI = {
  getAll: (params?: any) =>
    apiClient.get('/products', { params }),
  
  getById: (id: number) =>
    apiClient.get(`/products/${id}`),
  
  create: (data: any) =>
    apiClient.post('/products', data),
  
  update: (id: number, data: any) =>
    apiClient.put(`/products/${id}`, data),
  
  delete: (id: number) =>
    apiClient.delete(`/products/${id}`),
};

// دوال مساعدة لطلبات المبيعات
export const ordersAPI = {
  getAll: (params?: any) =>
    apiClient.get('/orders', { params }),
  
  getById: (id: number) =>
    apiClient.get(`/orders/${id}`),
  
  create: (data: any) =>
    apiClient.post('/orders', data),
  
  update: (id: number, data: any) =>
    apiClient.put(`/orders/${id}`, data),
  
  delete: (id: number) =>
    apiClient.delete(`/orders/${id}`),
};

// دوال مساعدة للفواتير
export const invoicesAPI = {
  getAll: (params?: any) =>
    apiClient.get('/invoices', { params }),
  
  getById: (id: number) =>
    apiClient.get(`/invoices/${id}`),
  
  create: (data: any) =>
    apiClient.post('/invoices', data),
  
  update: (id: number, data: any) =>
    apiClient.put(`/invoices/${id}`, data),
  
  delete: (id: number) =>
    apiClient.delete(`/invoices/${id}`),
};

// دوال مساعدة للتقارير
export const reportsAPI = {
  getDashboard: () =>
    apiClient.get('/reports/dashboard'),
  
  getSalesReport: (params?: any) =>
    apiClient.get('/reports/sales', { params }),
  
  getInventoryReport: (params?: any) =>
    apiClient.get('/reports/inventory', { params }),
  
  getFinancialReport: (params?: any) =>
    apiClient.get('/reports/financial', { params }),
};
