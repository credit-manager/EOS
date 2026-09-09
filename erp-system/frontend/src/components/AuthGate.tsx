import { useEffect, useState, type ReactNode } from 'react';
import { authAPI } from '../services/api';
import Login from './Login';

export default function AuthGate({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);

  const clearSession = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('eos_tenant_id');
    localStorage.removeItem('eos_company_id');
    localStorage.removeItem('eos_user');
    setAuthenticated(false);
  };

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setChecking(false);
      return;
    }

    authAPI.getCurrentUser()
      .then((response) => {
        const user = response.data?.data;
        if (!user?.tenant_id) throw new Error('Invalid session');
        localStorage.setItem('eos_tenant_id', String(user.tenant_id));
        if (user.company_id) localStorage.setItem('eos_company_id', String(user.company_id));
        localStorage.setItem('eos_user', JSON.stringify(user));
        setAuthenticated(true);
      })
      .catch(clearSession)
      .finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    const onExpired = () => clearSession();
    window.addEventListener('eos:auth-expired', onExpired);
    return () => window.removeEventListener('eos:auth-expired', onExpired);
  }, []);

  if (checking) return <main className="eos-auth-loading" aria-live="polite">EOS</main>;
  if (!authenticated) return <Login onAuthenticated={() => setAuthenticated(true)} />;
  return <>{children}</>;
}
