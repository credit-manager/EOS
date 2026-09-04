import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('eos_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('eos_token')
      localStorage.removeItem('eos_tenant_id')
      localStorage.removeItem('eos_user')
      if (window.location.pathname !== '/ui/login') window.location.replace('/ui/login')
    }
    return Promise.reject(error)
  },
)

export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  me: () => api.get('/auth/me'),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => api.post('/auth/reset-password', { token, new_password: newPassword }),
  verifyEmail: (token) => api.post('/auth/verify-email', { token }),
}

export const builderAPI = {
  compose: (description) => api.post('/dynamic/composer/compose', { input: description }),
  getSession: (sessionId) => api.get(`/dynamic/composer/sessions/${sessionId}`),
  approve: (sessionId) => api.post(`/dynamic/composer/sessions/${sessionId}/approve`, {}),
  activate: (sessionId) => api.post(`/dynamic/composer/sessions/${sessionId}/activate`),
}

export default api
