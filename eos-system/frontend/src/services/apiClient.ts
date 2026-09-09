/**
 * EOS System — API Client
 * Centralized HTTP client for all API calls.
 * P66 additions:
 *  - Offline-aware writes: failed POST/PUT/DELETE are queued & auto-replayed
 *  - Session-expiry broadcast (`eos-session-expired`) consumed by authStore
 *  - Silent token refresh when the access token expires mid-session
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { enqueueQueuedRequest } from './offlineQueue';
import { isTokenExpired, getToken, setTokens } from '../utils/jwt';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/** Auth endpoints must never be queued offline */
function isAuthPath(url?: string): boolean {
  return !!url && url.includes('/auth/');
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      async (config) => {
        const token = getToken();

        // P66: proactively detect an expired access token
        if (token && isTokenExpired(token)) {
          const refreshed = await this.trySilentRefresh();
          if (!refreshed) {
            this.broadcastSessionExpired();
            return Promise.reject(
              Object.assign(new Error('session expired'), { sessionExpired: true })
            );
          }
        }

        const activeToken = getToken();
        if (activeToken) {
          config.headers.Authorization = `Bearer ${activeToken}`;
        }

        // Add tenant ID from URL or storage
        const tenantId = this.getTenantId();
        if (tenantId) {
          config.headers['X-Tenant-ID'] = tenantId;
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        const networkFailure = !error.response;

        // ── P66: Offline queue for writes lost to connectivity ──
        if (
          networkFailure &&
          originalRequest &&
          !originalRequest._retriedOffline &&
          !isAuthPath(originalRequest.url)
        ) {
          const method = String(originalRequest.method || '').toLowerCase();
          if (method === 'post' || method === 'put' || method === 'delete') {
            enqueueQueuedRequest({
              url: originalRequest.url,
              method: method as 'post' | 'put' | 'delete',
              data: originalRequest.data,
            });
            return Promise.reject(
              Object.assign(error, { queuedOffline: true })
            );
          }
        }

        // Handle 401 errors (token expired)
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshed = await this.trySilentRefresh();
            if (refreshed) {
              originalRequest.headers.Authorization = `Bearer ${getToken()}`;
              return this.client(originalRequest);
            }
            this.broadcastSessionExpired();
          } catch (refreshError) {
            this.broadcastSessionExpired();
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /** Attempt one silent refresh using the stored refresh token */
  private async trySilentRefresh(): Promise<boolean> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const access = response.data?.access_token;
      if (!access) return false;
      const newRefresh = response.data?.refresh_token ?? refreshToken;
      setTokens(access, newRefresh);
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', newRefresh);
      return true;
    } catch {
      localStorage.removeItem('refresh_token');
      return false;
    }
  }

  /** Tell the whole app the session ended */
  private broadcastSessionExpired(): void {
    window.dispatchEvent(new CustomEvent('eos-session-expired'));
    window.location.href = '/login';
  }

  private getTenantId(): string | null {
    // Get tenant ID from URL path or localStorage
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length >= 3 && pathParts[1] === 't') {
      return pathParts[2];
    }
    return localStorage.getItem('tenant_id');
  }

  // Generic request methods
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  // File upload
  async upload<T>(url: string, file: File, fieldName: string = 'file'): Promise<T> {
    const formData = new FormData();
    formData.append(fieldName, file);

    const response = await this.client.post<T>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  // Download file
  async download(url: string, filename: string): Promise<void> {
    const response = await this.client.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(link.href);
  }
}

export const apiClient = new ApiClient();
export default apiClient;
