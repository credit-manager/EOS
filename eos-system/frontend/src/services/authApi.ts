/**
 * EOS System — Auth API Service
 */

import apiClient from './apiClient';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
} from '../types';

export const authApi = {
  // Login
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', data);
    
    // Store tokens
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    localStorage.setItem('tenant_id', data.tenant_id);
    
    return response;
  },

  // Register
  register: async (data: RegisterRequest) => {
    return apiClient.post('/auth/register', data);
  },

  // Refresh token
  refreshToken: async (refreshToken: string) => {
    return apiClient.post('/auth/refresh', { refresh_token: refreshToken });
  },

  // Get current user
  getMe: async (): Promise<User> => {
    return apiClient.get<User>('/auth/me');
  },

  // Change password
  changePassword: async (currentPassword: string, newPassword: string) => {
    return apiClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  // Forgot password
  forgotPassword: async (email: string) => {
    return apiClient.post('/auth/forgot-password', { email });
  },

  // Reset password
  resetPassword: async (token: string, newPassword: string) => {
    return apiClient.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  },

  // Logout
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('tenant_id');
    window.location.href = '/login';
  },
};

export default authApi;
