import { useEffect, useState } from 'react';
import { api, logoutSession, refreshToken, REFRESH_TOKEN_KEY, SESSION_KEY, TOKEN_KEY } from '../api';
import type { Session } from '../types';
import { AuthScreen } from './AuthScreen';
import { CatalogPage } from './CatalogPage';
import { EntityPage } from './EntityPage';
import { MetadataStudio } from './MetadataStudio';
import { WorkspacePage } from './WorkspacePage';

const DEFAULT_ENTITY = import.meta.env.VITE_ENTITY_CODE ?? '';
function sessionFromStorage(): Session | null {
  const stored = localStorage.getItem(SESSION_KEY);
  if (stored) { try { const parsed = JSON.parse(stored) as Session; if (parsed.access_token) return parsed; } catch { localStorage.removeItem(SESSION_KEY); } }
  const token = localStorage.getItem(TOKEN_KEY);
  const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
  return token ? { access_token: token, user_id: '', tenant_id: '', role: '', expires_in: 0, refresh_token: refresh ?? undefined } : null;
}
type Route = { kind: 'workspace' } | { kind: 'objects' } | { kind: 'entity'; code: string } | { kind: 'builder' };
function readRoute(): Route { const path = window.location.hash.replace(/^#/, '') || '/workspace'; const entity = path.match(/^\/objects\/([^/]+)$/); if (entity) return { kind: 'entity', code: decodeURIComponent(entity[1]) }; if (path === '/objects') return { kind: 'objects' }; if (path === '/builder') return { kind: 'builder' }; return { kind: 'workspace' }; }
const navigate = (path: string) => { window.location.hash = path; };
export default function PlatformApp() {
  const [session, setSession] = useState<Session | null>(() => sessionFromStorage());
  const [route, setRoute] = useState<Route>(() => readRoute());
  const [hydrating, setHydrating] = useState(Boolean(session));
  useEffect(() => { const onHash = () => setRoute(readRoute()); window.addEventListener('hashchange', onHash); if (!window.location.hash) navigate(DEFAULT_ENTITY ? `/objects/${DEFAULT_ENTITY}` : '/workspace'); return () => window.removeEventListener('hashchange', onHash); }, []);
  useEffect(() => { if (!session) { setHydrating(false); return; } if (session.user_id && session.role) { setHydrating(false); return; } let active = true; void api<{ user_id: string; tenant_id: string; role: string }>('/auth/me', session.access_token).then((me) => { if (active) setSession((current) => current ? { ...current, user_id: me.user_id, tenant_id: me.tenant_id, role: me.role } : current); }).catch(() => { if (active) { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_TOKEN_KEY); localStorage.removeItem(SESSION_KEY); setSession(null); } }).finally(() => { if (active) setHydrating(false); }); return () => { active = false; }; }, [session]);
  useEffect(() => { if (!session?.refresh_token || session.expires_in <= 0) return; const delay = session.expires_at ? Math.max(1000, session.expires_at - Date.now() - 60000) : Math.max(1000, session.expires_in * 1000 - 60000); const timer = window.setTimeout(() => { void refreshToken(session.refresh_token!).then(authenticated).catch(() => void logout()); }, delay); return () => window.clearTimeout(timer); }, [session]);
  function authenticated(data: Session) { const next = { ...data, expires_at: Date.now() + data.expires_in * 1000 }; localStorage.setItem(TOKEN_KEY, next.access_token); if (next.refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, next.refresh_token); localStorage.setItem(SESSION_KEY, JSON.stringify(next)); setSession(next); setHydrating(false); }
  async function logout() { const token = session?.access_token; if (token) { try { await logoutSession(token); } catch {} } localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_TOKEN_KEY); localStorage.removeItem(SESSION_KEY); setSession(null); navigate('/workspace'); }
  if (hydrating) return <main className="shell"><section className="card"><p className="muted">Restoring your workspace…</p></section></main>;
  if (!session) return <AuthScreen onAuthenticated={authenticated} />;
  if (route.kind === 'builder' && session.role === 'admin') return <main className="shell"><header className="hero"><div><p className="eyebrow">2TO / EOS</p><h1>Metadata Studio</h1></div><button className="secondary" onClick={() => navigate('/objects')}>Back</button></header><MetadataStudio token={session.access_token} defaultCode={DEFAULT_ENTITY} onCreated={(code) => navigate(`/objects/${encodeURIComponent(code)}`)} /></main>;
  if (route.kind === 'entity') return <EntityPage token={session.access_token} role={session.role} entityCode={route.code} onLogout={() => void logout()} onBack={() => navigate('/objects')} />;
  if (route.kind === 'objects') return <CatalogPage token={session.access_token} role={session.role} defaultEntity={DEFAULT_ENTITY} onSelect={(code) => navigate(`/objects/${encodeURIComponent(code)}`)} onLogout={() => void logout()} onCreate={() => navigate('/builder')} />;
  return <WorkspacePage token={session.access_token} onOpenObjects={() => navigate('/objects')} />;
}
