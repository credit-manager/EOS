import { useState } from 'react';
import { authenticate } from '../api';
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

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const path = mode === 'login' ? '/auth/token' : '/auth/register';
      const body =
        mode === 'login' ? { email, password } : { email, password, tenant_name: tenantName };
      const data = await authenticate(path, body);
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
