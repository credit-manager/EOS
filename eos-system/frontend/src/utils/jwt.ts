/**
 * EOS System — JWT Utilities (P66)
 * Minimal client-side token inspection for session-expiry awareness.
 */

const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

export interface TokenClaims {
  sub?: string;
  exp?: number;
  iat?: number;
  tenant_id?: string;
  email?: string;
  roles?: string[];
}

function base64UrlDecode(input: string): string {
  const pad = input.length % 4 === 0 ? '' : '='.repeat(4 - (input.length % 4));
  const b64 = input.replace(/-/g, '+').replace(/_/g, '/') + pad;
  return atob(b64);
}

/** Decode a JWT payload without verifying the signature (client display only) */
export function decodeToken(token: string | null): TokenClaims | null {
  if (!token) return null;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null; // not a JWT (e.g. dev mock token)
    return JSON.parse(base64UrlDecode(parts[1])) as TokenClaims;
  } catch {
    return null;
  }
}

/** True when a real JWT exists and its exp has passed */
export function isTokenExpired(token: string | null): boolean {
  const claims = decodeToken(token);
  if (!claims?.exp) return false; // non-JWT tokens: let server decide
  return Date.now() / 1000 >= claims.exp;
}

/** Seconds remaining before expiry (Infinity for non-JWT) */
export function secondsUntilExpiry(token: string | null): number {
  const claims = decodeToken(token);
  if (!claims?.exp) return Infinity;
  return claims.exp - Date.now() / 1000;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh?: string | null): void {
  localStorage.setItem(TOKEN_KEY, access);
  if (refresh !== undefined && refresh !== null) {
    localStorage.setItem(REFRESH_KEY, refresh);
  }
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}
