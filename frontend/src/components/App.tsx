import { useState, useEffect } from 'react';
import { api, TOKEN_KEY, REFRESH_TOKEN_KEY } from '../api';
import type { Session } from '../types';
import { AuthScreen } from './AuthScreen';
import { CatalogPage } from './CatalogPage';
import { EntityPage } from './EntityPage';
import { MetadataStudio } from './MetadataStudio';

const DEFAULT_ENTITY = import.meta.env.VITE_ENTITY_CODE ?? '';

function sessionFromStorage(): Session | null {
  const token = localStorage.getItem(TOKEN_KEY);
  const refreshTokenValue = localStorage.getItem(REFRESH_TOKEN_KEY);
  return token
    ? {
        access_token: token,
        user_id: '',
        tenant_id: '',
        role: '',
        expires_in: 0,
        refresh_token: refreshTokenValue ?? undefined,
      }
    : null;
}

export function App() {
  const [session, setSession] = useState<Session | null>(() => sessionFromStorage());
  const [entityCode, setEntityCode] = useState<string | null>(DEFAULT_ENTITY || null);
  const [studioOnly, setStudioOnly] = useState(false);
  const [hydrating, setHydrating] = useState(Boolean(session));

  useEffect(() => {
    if (!session) {
      setHydrating(false);
      return;
    }
    if (session.user_id && session.role) {
      setHydrating(false);
      return;
    }
    let active = true;
    void api<{ user_id: string; tenant_id: string; role: string; email: string }>(
      '/auth/me',
      session.access_token
    )
      .then((me) => {
        if (active)
          setSession((current) =>
            current
              ? { ...current, user_id: me.user_id, tenant_id: me.tenant_id, role: me.role }
              : current
          );
      })
      .catch(() => {
        if (active) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(REFRESH_TOKEN_KEY);
          setSession(null);
          setEntityCode(null);
        }
      })
      .finally(() => {
        if (active) setHydrating(false);
      });
    return () => {
      active = false;
    };
  }, [session]);

  function authenticated(data: Session) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    if (data.refresh_token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
    }
    setSession(data);
    setHydrating(false);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setSession(null);
    setEntityCode(null);
    setStudioOnly(false);
  }

  if (hydrating) {
    return (
      <main className="shell">
        <section className="card">
          <p className="muted">Restoring your workspace…</p>
        </section>
      </main>
    );
  }

  if (!session) return <AuthScreen onAuthenticated={authenticated} />;

  if (studioOnly && session.role === 'admin') {
    return (
      <main className="shell">
        <header className="hero">
          <div>
            <p className="eyebrow">2TO / EOS</p>
            <h1>Metadata Studio</h1>
          </div>
          <button className="secondary" onClick={() => setStudioOnly(false)}>
            Back
          </button>
        </header>
        <MetadataStudio
          token={session.access_token}
          defaultCode={DEFAULT_ENTITY}
          onCreated={(code) => {
            setStudioOnly(false);
            setEntityCode(code);
          }}
        />
      </main>
    );
  }

  if (entityCode) {
    return (
      <EntityPage
        token={session.access_token}
        role={session.role}
        entityCode={entityCode}
        onLogout={logout}
        onBack={() => setEntityCode(null)}
      />
    );
  }

  return (
    <CatalogPage
      token={session.access_token}
      role={session.role}
      defaultEntity={DEFAULT_ENTITY}
      onSelect={(code) => {
        setEntityCode(code);
        setStudioOnly(false);
      }}
      onLogout={logout}
      onCreate={() => setStudioOnly(true)}
    />
  );
}
