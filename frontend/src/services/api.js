import axios from 'axios'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('eos_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Add tenant ID if available
    const tenantId = localStorage.getItem('eos_tenant_id')
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('eos_token')
      localStorage.removeItem('eos_tenant_id')
      window.location.href = '/login'
    }
    
    if (error.response?.status === 403) {
      // Access denied
      console.error('Access denied to resource')
    }
    
    return Promise.reject(error)
  }
)

// Auth APIs
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  refreshToken: () => api.post('/auth/refresh'),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, password) => api.post(`/auth/reset-password/${token}`, { password }),
  verify2FA: (code) => api.post('/auth/verify-2fa', { code }),
}

// Industry APIs
export const industryAPI = {
  list: () => api.get('/industries'),
  get: (id) => api.get(`/industries/${id}`),
  select: (industryId) => api.post('/industries/select', { industry_id: industryId }),
}

// Builder APIs
export const builderAPI = {
  compose: (description) => api.post('/builder/compose', { description }),
  preview: (configId) => api.get(`/builder/preview/${configId}`),
  publish: (configId) => api.post(`/builder/publish/${configId}`),
  getStatus: (buildId) => api.get(`/builder/status/${buildId}`),
}

// Entity APIs
export const entityAPI = {
  list: () => api.get('/entities'),
  get: (entityName) => api.get(`/entities/${entityName}`),
  create: (entityData) => api.post('/entities', entityData),
  update: (entityName, data) => api.put(`/entities/${entityName}`, data),
  delete: (entityName) => api.delete(`/entities/${entityName}`),
  
  // Dynamic CRUD operations
  getRows: (entityName, params) => api.get(`/dynamic/${entityName}`, { params }),
  createRow: (entityName, data) => api.post(`/dynamic/${entityName}`, data),
  updateRow: (entityName, id, data) => api.put(`/dynamic/${entityName}/${id}`, data),
  deleteRow: (entityName, id) => api.delete(`/dynamic/${entityName}/${id}`),
}

// Report APIs
export const reportAPI = {
  financial: (type, params) => api.get(`/reports/financial/${type}`, { params }),
  operational: (type, params) => api.get(`/reports/operational/${type}`, { params }),
  custom: (reportId, params) => api.get(`/reports/custom/${reportId}`, { params }),
  export: (reportId, format) => api.get(`/reports/export/${reportId}?format=${format}`),
}

// Settings APIs
export const settingsAPI = {
  getProfile: () => api.get('/settings/profile'),
  updateProfile: (data) => api.put('/settings/profile', data),
  getCompany: () => api.get('/settings/company'),
  updateCompany: (data) => api.put('/settings/company', data),
  getUsers: () => api.get('/settings/users'),
  createUser: (data) => api.post('/settings/users', data),
  updateUser: (userId, data) => api.put(`/settings/users/${userId}`, data),
  deleteUser: (userId) => api.delete(`/settings/users/${userId}`),
  getRoles: () => api.get('/settings/roles'),
  createRole: (data) => api.post('/settings/roles', data),
  updateRole: (roleId, data) => api.put(`/settings/roles/${roleId}`, data),
  deleteRole: (roleId) => api.delete(`/settings/roles/${roleId}`),
}

// Tenant APIs
export const tenantAPI = {
  list: () => api.get('/tenants'),
  create: (data) => api.post('/tenants', data),
  get: (id) => api.get(`/tenants/${id}`),
  update: (id, data) => api.put(`/tenants/${id}`, data),
  delete: (id) => api.delete(`/tenants/${id}`),
  switchTenant: (id) => api.post(`/tenants/switch/${id}`),
}

export default api
