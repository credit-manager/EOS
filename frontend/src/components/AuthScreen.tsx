import { useState } from 'react';
import { API, TOKEN_KEY, REFRESH_TOKEN_KEY } from '../api';
import type { Session } from '../types';

interface AuthScreenProps {
  onAuthenticated: (session: Session) => void;
}

export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [tenantName, setTenantName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function ssoLogin(provider: string) {
    try {
      const res = await fetch(`${API}/auth/sso/auth-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, redirect_uri: `${window.location.origin}/auth/sso/callback` }),
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.auth_url) window.location.href = data.auth_url;
    } catch { /* ignore */ }
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const path = mode === 'login' ? '/auth/token' : '/auth/register';
      const body =
        mode === 'login' ? { email, password } : { email, password, tenant_name: tenantName };
      const response = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
      const data = (await response.json()) as Session;
      localStorage.setItem(TOKEN_KEY, data.access_token);
      if (data.refresh_token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      }
      onAuthenticated(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell auth-shell">
      <section className="card auth-card">
        <p className="eyebrow">2TO / EOS</p>
        <h1>{mode === 'login' ? 'Sign in' : 'Create your workspace'}</h1>
        <p className="muted">Your workspace and permissions come from the signed access token.</p>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        <label>
          <span>Email</span>
          <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        </label>
        <label>
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          />
        </label>
        {mode === 'register' && (
          <label>
            <span>Workspace name</span>
            <input value={tenantName} onChange={(e) => setTenantName(e.target.value)} />
          </label>
        )}
        <button
          disabled={
            busy ||
            !email ||
            password.length < (mode === 'register' ? 12 : 1) ||
            (mode === 'register' && !tenantName)
          }
          onClick={() => void submit()}
        >
          {busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Create workspace'}
        </button>
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-xs text-gray-400">Or continue with</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void ssoLogin('google')} className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50 transition-colors">
            Google
          </button>
          <button type="button" onClick={() => void ssoLogin('microsoft')} className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50 transition-colors">
            Microsoft
          </button>
        </div>
        <button
          className="secondary"
          onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
        >
          {mode === 'login' ? 'Create a new workspace' : 'I already have an account'}
        </button>
      </section>
    </main>
  );
}
