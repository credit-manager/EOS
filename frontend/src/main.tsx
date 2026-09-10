import { StrictMode, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Field = { code: string; type: string; required: boolean; label?: string | null };
type Definition = { code: string; name: string; fields: Field[] };
type Metadata = { definition: Definition; version: number; published: boolean };
type RecordItem = { id: string; data: Record<string, unknown>; version: number };

const API = import.meta.env.VITE_API_URL ?? '/api/v1';
const TENANT = import.meta.env.VITE_TENANT_ID ?? '00000000-0000-0000-0000-000000000001';
const ENTITY = 'subcontractor_evaluation';

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': TENANT, ...(init.headers ?? {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function App() {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fields = useMemo(() => metadata?.definition.fields ?? [], [metadata]);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [meta, items] = await Promise.all([
        api<Metadata>(`/metadata/entities/${ENTITY}`),
        api<RecordItem[]>(`/entities/${ENTITY}/records`),
      ]);
      setMetadata(meta);
      setRecords(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load entity');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function create() {
    setError(null);
    try {
      const data: Record<string, unknown> = {};
      for (const field of fields) {
        const raw = form[field.code] ?? '';
        data[field.code] = field.type === 'integer' ? Number(raw) : raw;
      }
      await api(`/entities/${ENTITY}/records`, { method: 'POST', body: JSON.stringify({ data }) });
      setForm({});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create record');
    }
  }

  async function remove(record: RecordItem) {
    setError(null);
    try {
      await api(`/entities/${ENTITY}/records/${record.id}`, { method: 'DELETE' });
      setRecords((current) => current.filter((item) => item.id !== record.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete record');
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div><p className="eyebrow">2TO / EOS</p><h1>{metadata?.definition.name ?? 'Metadata Entity'}</h1></div>
        <div className="pill">{metadata ? `v${metadata.version} · Published` : 'Loading metadata'}</div>
      </header>
      {error && <div className="error" role="alert">{error}</div>}
      <section className="card">
        <h2>New record</h2>
        <div className="grid">
          {fields.map((field) => (
            <label key={field.code}>
              <span>{field.label ?? field.code}{field.required ? ' *' : ''}</span>
              <input
                type={field.type === 'integer' ? 'number' : 'text'}
                value={form[field.code] ?? ''}
                onChange={(event) => setForm({ ...form, [field.code]: event.target.value })}
              />
            </label>
          ))}
        </div>
        <button disabled={busy || fields.length === 0} onClick={() => void create()}>Create record</button>
      </section>
      <section className="card">
        <div className="section-head"><h2>Records</h2><button className="secondary" onClick={() => void load()}>Refresh</button></div>
        {records.length === 0 ? <p className="muted">No records yet.</p> : (
          <div className="table-wrap"><table><thead><tr><th>ID</th>{fields.map((field) => <th key={field.code}>{field.label ?? field.code}</th>)}<th /></tr></thead>
            <tbody>{records.map((record) => <tr key={record.id}><td>{record.id.slice(0, 8)}…</td>{fields.map((field) => <td key={field.code}>{String(record.data[field.code] ?? '')}</td>)}<td><button className="danger" onClick={() => void remove(record)}>Delete</button></td></tr>)}</tbody>
          </table></div>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
