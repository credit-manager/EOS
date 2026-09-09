import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { setTokens, clearTokens } from '../utils/jwt';

interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  tenantId: string;
  roles: string[];
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      accessToken: null,
      refreshToken: null,
      
      login: async (email: string, password: string) => {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err?.detail?.error?.message || 'Login failed');
        }

        const json = await response.json();
        const data = json.data || json;
        const token = data.access_token;
        const userData = data.user;

        if (!token) throw new Error('No token received');

        setTokens(token, null);
        localStorage.setItem('tenant_id', userData.tenant_id || '');

        // Fetch tenant info (industry, modules) in background
        fetch(`${API_BASE_URL}/control/tenants/${userData.tenant_id}/info`, {
          headers: { Authorization: `Bearer ${token}` },
        })
          .then(r => r.json())
          .then(info => {
            if (info.industry) {
              localStorage.setItem('tenant_industry', info.industry);
              localStorage.setItem('tenant_company_name', info.company_name || '');
              localStorage.setItem('tenant_modules', JSON.stringify(info.modules || []));
            }
          })
          .catch(() => {});

        set({
          isAuthenticated: true,
          user: {
            id: userData.id,
            email: userData.email,
            firstName: userData.first_name || '',
            lastName: userData.last_name || '',
            tenantId: userData.tenant_id || '',
            roles: userData.role ? [userData.role] : userData.roles || [],
          },
          accessToken: token,
          refreshToken: null,
        });
      },
      
      logout: () => {
        clearTokens();
        localStorage.removeItem('tenant_id');
        localStorage.removeItem('eos-auth-storage');
        set({
          isAuthenticated: false,
          user: null,
          accessToken: null,
          refreshToken: null,
        });
      },
      
      setUser: (user) => {
        set({ user });
      },
      
      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken });
      },
    }),
    {
      name: 'eos-auth-storage',
    }
  )
);

// P66: react to server-declared session expiry broadcast from apiClient
if (typeof window !== 'undefined') {
  window.addEventListener('eos-session-expired', () => {
    useAuthStore.getState().logout();
  });
}
