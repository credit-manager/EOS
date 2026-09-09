/**
 * EOS System — White-Label API Service (P67)
 */

import apiClient from './apiClient';
import type { TenantBranding, PublicBranding, FeatureFlags } from '../types';

export const whitelabelApi = {
  getBranding: async (tenantId: string): Promise<{ status: string; data: TenantBranding }> => {
    return apiClient.get('/whitelabel/branding', { params: { tenant_id: tenantId } });
  },

  updateBranding: async (
    tenantId: string,
    payload: Partial<TenantBranding>
  ): Promise<{ status: string; data: TenantBranding }> => {
    return apiClient.put('/whitelabel/branding', payload, {
      params: { tenant_id: tenantId },
    });
  },

  getFlags: async (tenantId: string): Promise<{ status: string; data: FeatureFlags }> => {
    return apiClient.get('/whitelabel/branding/flags', { params: { tenant_id: tenantId } });
  },

  setFlag: async (
    tenantId: string,
    flag: keyof FeatureFlags,
    enabled: boolean
  ): Promise<{ status: string; data: FeatureFlags }> => {
    return apiClient.put(
      `/whitelabel/branding/flags/${flag}`,
      null,
      { params: { tenant_id: tenantId, enabled } }
    );
  },

  claimDomain: async (
    tenantId: string,
    customDomain: string
  ): Promise<{ status: string; data: TenantBranding }> => {
    return apiClient.post(
      '/whitelabel/domain/claim',
      { custom_domain: customDomain },
      { params: { tenant_id: tenantId } }
    );
  },

  verifyDomain: async (tenantId: string): Promise<{ status: string; data: TenantBranding }> => {
    return apiClient.post('/whitelabel/domain/verify', null, {
      params: { tenant_id: tenantId },
    });
  },

  removeDomain: async (tenantId: string): Promise<{ status: string; data: TenantBranding }> => {
    return apiClient.delete('/whitelabel/domain', { params: { tenant_id: tenantId } });
  },

  /** Public — resolves login-page branding by domain or slug (no auth) */
  getPublicBranding: async (domainOrSlug: string): Promise<PublicBranding> => {
    const res = await axioslessGetPublic(domainOrSlug);
    return res;
  },
};

/**
 * Public endpoint should not carry auth headers / tenant scoping.
 * Uses a bare fetch to avoid the interceptor stack entirely.
 */
async function axioslessGetPublic(domainOrSlug: string): Promise<PublicBranding> {
  const base =
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) ||
    'http://localhost:8000/api/v1';
  const res = await fetch(`${base}/whitelabel/public/${encodeURIComponent(domainOrSlug)}`);
  if (!res.ok) throw new Error(`public branding failed: ${res.status}`);
  const json = await res.json();
  return json.data as PublicBranding;
}

export default whitelabelApi;
