import { StrictMode, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Field = {
  code: string;
  type: 'text' | 'integer' | 'decimal' | 'boolean' | 'date' | 'uuid';
  required: boolean;
  nullable: boolean;
  label?: string | null;
};
type Definition = { code: string; name: string; fields: Field[] };
type Metadata = { definition: Definition; version: number; published: boolean };
type RecordItem = { id: string; data: Record<string, unknown>; version: number };
type Session = { access_token: string; tenant_id: string; role: string; expires_in: number };

type FormField = { code: string; type: Field['type']; required: boolean; label: string };

const API = import.meta.env.VITE_API_URL ?? '/api/v1';
const ENTITY = import.meta.env.VITE_ENTITY_CODE ?? 'subcontractor_evaluation';
const TOKEN_KEY = '2to_eos_access_token';

function sessionFromStorage(): Session | null {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { access_token: token, tenant_id: '', role: '', expires_in: 0 } : null;
}

async function api<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (session: Session) => void }) {
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
      const body = mode === 'login' ? { email, password } : { email, password, tenant_name: tenantName };
      const session = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!session.ok) throw new Error((await session.text()) || `HTTP ${session.status}`);
      const data = (await session.json()) as Session;
      localStorage.setItem(TOKEN_KEY, data.access_token);
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
        <p className="muted">Identity and tenant context are supplied by the signed access token.</p>
        {error && <div className="error" role="alert">{error}</div>}
        <label><span>Email</span><input value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
        <label><span>Password</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /></label>
        {mode === 'register' && <label><span>Workspace name</span><input value={tenantName} onChange={(event) => setTenantName(event.target.value)} /></label>}
        <button disabled={busy || !email || password.length < (mode === 'register' ? 12 : 1) || (mode === 'register' && !tenantName)} onClick={() => void submit()}>
          {busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Create workspace'}
        </button>
        <button className="secondary" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Create a new workspace' : 'I already have an account'}
        </button>
      </section>
    </main>
  );
}

function MetadataStudio({ token, onChanged }: { token: string; onChanged: () => void }) {
  const [code, setCode] = useState(ENTITY);
  const [name, setName] = useState('Subcontractor Evaluation');
  const [fields, setFields] = useState<FormField[]>([
    { code: 'quality', type: 'integer', required: true, label: 'Quality' },
    { code: 'safety', type: 'integer', required: true, label: 'Safety' },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function updateField(index: number, patch: Partial<FormField>) {
    setFields((current) => current.map((field, position) => position === index ? { ...field, ...patch } : field));
  }

  async function createMetadata() {
    setError(null);
    setMessage(null);
    try {
      const created = await api<Metadata>('/metadata/entities', token, {
        method: 'POST',
        body: JSON.stringify({ code, name, fields: fields.map((field) => ({ ...field, nullable: false })) }),
      });
      await api(`/metadata/entities/${created.definition.code}/publish`, token, { method: 'POST' });
      setMessage(`Published ${created.definition.code} v${created.version}.`);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to publish metadata');
    }
  }

  return (
    <section className="card">
      <div className="section-head"><div><p className="eyebrow">Metadata Studio</p><h2>Define an entity</h2></div></div>
      {error && <div className="error" role="alert">{error}</div>}
      {message && <div className="success" role="status">{message}</div>}
      <div className="grid">
        <label><span>Entity code</span><input value={code} onChange={(event) => setCode(event.target.value)} /></label>
        <label><span>Display name</span><input value={name} onChange={(event) => setName(event.target.value)} /></label>
      </div>
      <div className="field-list">
        {fields.map((field, index) => (
          <div className="field-row" key={`${index}-${field.code}`}>
            <input value={field.code} onChange={(event) => updateField(index, { code: event.target.value })} aria-label="Field code" />
            <select value={field.type} onChange={(event) => updateField(index, { type: event.target.value as Field['type'] })} aria-label="Field type">
              <option value="text">Text</option><option value="integer">Integer</option><option value="decimal">Decimal</option>
              <option value="boolean">Boolean</option><option value="date">Date</option><option value="uuid">UUID</option>
            </select>
            <input value={field.label} onChange={(event) => updateField(index, { label: event.target.value })} aria-label="Field label" />
            <label className="inline-check"><input type="checkbox" checked={field.required} onChange={(event) => updateField(index, { required: event.target.checked })} /> Required</label>
            <button className="danger" onClick={() => setFields((current) => current.filter((_, position) => position !== index))}>Remove</button>
          </div>
        ))}
      </div>
      <div className="actions"><button className="secondary" onClick={() => setFields((current) => [...current, { code: `field_${current.length + 1}`, type: 'text', required: false, label: `Field ${current.length + 1}` }])}>Add field</button><button disabled={!code || !name || fields.length === 0} onClick={() => void createMetadata()}>Publish entity</button></div>
    </section>
  );
}

function EntityPage({ token, role, onLogout }: { token: string; role: string; onLogout: () => void }) {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [form, setForm] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const fields = useMemo(() => metadata?.definition.fields ?? [], [metadata]);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [meta, items] = await Promise.all([
        api<Metadata>(`/metadata/entities/${ENTITY}`, token),
        api<RecordItem[]>(`/entities/${ENTITY}/records`, token),
      ]);
      setMetadata(meta);
      setRecords(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load entity');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, [refreshKey]);

  function setField(field: Field, value: string | boolean) {
    setForm((current) => ({ ...current, [field.code]: value }));
  }

  function serializeField(field: Field, value: string | boolean): unknown {
    if (field.type === 'integer') return Number(value);
    if (field.type === 'decimal') return value;
    if (field.type === 'boolean') return value;
    return value;
  }

  async function create() {
    setError(null);
    try {
      const data: Record<string, unknown> = {};
      for (const field of fields) data[field.code] = serializeField(field, form[field.code] ?? (field.type === 'boolean' ? false : ''));
      await api(`/entities/${ENTITY}/records`, token, { method: 'POST', body: JSON.stringify({ data }) });
      setForm({});
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create record');
    }
  }

  async function remove(record: RecordItem) {
    setError(null);
    try {
      await api(`/entities/${ENTITY}/records/${record.id}`, token, { method: 'DELETE' });
      setRecords((current) => current.filter((item) => item.id !== record.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete record');
    }
  }

  if (metadata === null && !busy) {
    return (
      <main className="shell">
        <header className="hero"><div><p className="eyebrow">2TO / EOS</p><h1>Metadata-first ERP</h1></div><button className="secondary" onClick={onLogout}>Sign out</button></header>
        {role === 'admin' && <MetadataStudio token={token} onChanged={() => setRefreshKey((key) => key + 1)} />}
        <section className="card"><h2>{ENTITY}</h2><p className="muted">This entity is not published for the current workspace yet.</p>{error && <div className="error" role="alert">{error}</div>}</section>
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="hero">
        <div><p className="eyebrow">2TO / EOS · {role}</p><h1>{metadata?.definition.name ?? ENTITY}</h1></div>
        <div className="actions"><div className="pill">{metadata ? `v${metadata.version} · Published` : 'Loading metadata'}</div><button className="secondary" onClick={onLogout}>Sign out</button></div>
      </header>
      {error && <div className="error" role="alert">{error}</div>}
      {role === 'admin' && <MetadataStudio token={token} onChanged={() => setRefreshKey((key) => key + 1)} />}
      <section className="card">
        <h2>New record</h2>
        <div className="grid">
          {fields.map((field) => (
            <label key={field.code}>
              <span>{field.label ?? field.code}{field.required ? ' *' : ''}</span>
              {field.type === 'boolean' ? (
                <input type="checkbox" checked={Boolean(form[field.code])} onChange={(event) => setField(field, event.target.checked)} />
              ) : (
                <input type={field.type === 'integer' || field.type === 'decimal' ? 'number' : field.type === 'date' ? 'date' : 'text'} value={String(form[field.code] ?? '')} onChange={(event) => setField(field, event.target.value)} />
              )}
            </label>
          ))}
        </div>
        <button disabled={busy || fields.length === 0} onClick={() => void create()}>Create record</button>
      </section>
      <section className="card">
        <div className="section-head"><h2>Records</h2><button className="secondary" onClick={() => setRefreshKey((key) => key + 1)}>Refresh</button></div>
        {records.length === 0 ? <p className="muted">No records yet.</p> : (
          <div className="table-wrap"><table><thead><tr><th>ID</th>{fields.map((field) => <th key={field.code}>{field.label ?? field.code}</th>)}<th /></tr></thead>
            <tbody>{records.map((record) => <tr key={record.id}><td>{record.id.slice(0, 8)}…</td>{fields.map((field) => <td key={field.code}>{String(record.data[field.code] ?? '')}</td>)}<td><button className="danger" onClick={() => void remove(record)}>Delete</button></td></tr>)}</tbody>
          </table></div>
        )}
      </section>
    </main>
  );
}

function App() {
  const [session, setSession] = useState<Session | null>(() => sessionFromStorage());

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setSession(null);
  }

  if (!session) return <AuthScreen onAuthenticated={setSession} />;
  return <EntityPage token={session.access_token} role={session.role} onLogout={logout} />;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
