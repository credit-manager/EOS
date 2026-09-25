export const API = import.meta.env.VITE_API_URL ?? '/api/v1';
export const DEFAULT_ENTITY = import.meta.env.VITE_ENTITY_CODE ?? '';
export const TOKEN_KEY = '2to_eos_access_token';
export const REFRESH_TOKEN_KEY = '2to_eos_refresh_token';

export async function api<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiWithRetry<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const maxRetries = 3;
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await api<T>(path, token, init);
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));

      const statusMatch = lastError.message.match(/HTTP (\d+)/);
      const status = statusMatch ? Number(statusMatch[1]) : 0;
      const isRetryable = status >= 500 || status === 0;

      if (!isRetryable || attempt === maxRetries) {
        throw lastError;
      }

      const delayMs = Math.pow(2, attempt) * 1000;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  throw lastError!;
}

export async function refreshToken(refreshToken: string): Promise<{
  access_token: string;
  refresh_token: string;
  user_id: string;
  tenant_id: string;
  role: string;
  expires_in: number;
  refresh_expires_in: number;
}> {
  const response = await fetch(`${API}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
  return response.json();
}
