/**
 * EOS System — Branding Store (P67)
 * Holds the resolved white-label branding for the active tenant and
 * applies it live to antd tokens, favicon and document title.
 */

import { create } from 'zustand';
import { whitelabelApi } from '../services/whitelabelApi';
import type { PublicBranding } from '../types';

export interface BrandingState {
  branding: PublicBranding | null;
  loaded: boolean;
  loading: boolean;
  loadBranding: (domainOrSlug?: string | null) => Promise<void>;
  applyLocalOverride: (patch: Partial<PublicBranding>) => void;
  resetBranding: () => void;
}

const PLATFORM_DEFAULTS: PublicBranding = {
  system_name_en: '2TO ERP Platform',
  system_name_ar: '2TO — منصة إدارة المؤسسات',
  logo_url: null,
  favicon_url: null,
  primary_color: '#006D77',
  secondary_color: '#4B0082',
  theme_mode: 'light',
  direction: 'rtl',
  login_title_en: 'Login to 2TO',
  login_title_ar: 'تسجيل الدخول إلى 2TO',
  login_subtitle_en: 'Enterprise Resource Planning for your business',
  login_subtitle_ar: 'إدارة موارد مؤسستك في مكان واحد',
};

function resolveBrand(branding: PublicBranding | null): PublicBranding {
  if (!branding) return PLATFORM_DEFAULTS;
  // Fill any missing/null field from platform defaults
  return { ...PLATFORM_DEFAULTS, ...pickDefined(branding) };
}

function pickDefined<T extends object>(obj: T): Partial<T> {
  const out: any = {};
  Object.entries(obj).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') out[k] = v;
  });
  return out;
}

function applyDocumentChrome(b: PublicBranding) {
  // Dynamic favicon
  try {
    let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = b.favicon_url || '/favicon.svg';
  } catch {
    /* non-critical */
  }

  // Theme color for mobile browser chrome
  const meta = document.querySelector<HTMLMetaElement>("meta[name='theme-color']");
  if (meta) meta.content = b.secondary_color || '#001529';

  // Document title reflects white-label name
  const title = b.direction === 'ltr' ? b.system_name_en : b.system_name_ar;
  if (title) document.title = `${title} — ${b.system_name_en === title ? '' : 'EOS'}`.trim();
}

export const useBrandingStore = create<BrandingState>()((set, get) => ({
  branding: null,
  loaded: false,
  loading: false,

  loadBranding: async (domainOrSlug?: string | null) => {
    // No identity hint yet → keep platform defaults, mark loaded
    if (!domainOrSlug) {
      set({ branding: resolveBrand(null), loaded: true, loading: false });
      applyDocumentChrome(get().branding!);
      return;
    }
    set({ loading: true });
    try {
      const data = await whitelabelApi.getPublicBranding(domainOrSlug);
      const brand = resolveBrand(data);
      set({ branding: brand, loaded: true, loading: false });
      applyDocumentChrome(brand);
    } catch {
      // Fallback silently to platform defaults
      const brand = resolveBrand(null);
      set({ branding: brand, loaded: true, loading: false });
      applyDocumentChrome(brand);
    }
  },

  applyLocalOverride: (patch) => {
    const merged = resolveBrand({ ...(get().branding ?? PLATFORM_DEFAULTS), ...patch } as PublicBranding);
    set({ branding: merged });
    applyDocumentChrome(merged);
  },

  resetBranding: () => {
    set({ branding: resolveBrand(null), loaded: true });
    applyDocumentChrome(get().branding!);
  },
}));

export { PLATFORM_DEFAULTS };
