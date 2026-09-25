import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';
import type { Metadata, RecordItem, Field, PermissionAction } from '../types';
import { useI18n } from '../i18n';
import { RelationField } from './RelationField';

interface EntityPageProps {
  token: string;
  role: string;
  entityCode: string;
  onLogout: () => void;
  onBack: () => void;
}

export function EntityPage({ token, role, entityCode, onLogout, onBack }: EntityPageProps) {
  const { t } = useI18n();
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [form, setForm] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fields = useMemo(() => metadata?.definition.fields ?? [], [metadata]);
  const permissions = metadata?.definition.permissions;

  const allowed = (action: PermissionAction) =>
    role === 'admin' ||
    permissions?.[role === 'member' ? 'member' : 'admin']?.includes(action) === true;

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [meta, items] = await Promise.all([
        api<Metadata>(`/metadata/entities/${entityCode}`, token),
        api<RecordItem[]>(`/entities/${entityCode}/records`, token),
      ]);
      setMetadata(meta);
      setRecords(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.entityPage.loadFailed);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityCode, token]);

  function setField(field: Field, value: string | boolean) {
    setForm((current) => ({ ...current, [field.code]: value }));
  }

  function serializeField(field: Field, value: string | boolean): unknown {
    if (field.type === 'integer') return Number(value);
    return value;
  }

  async function create() {
    setError(null);
    try {
      const data: Record<string, unknown> = {};
      for (const field of fields) {
        if (field.type === 'boolean') {
          data[field.code] = Boolean(form[field.code]);
        } else if (form[field.code] !== undefined && form[field.code] !== '') {
          data[field.code] = serializeField(field, form[field.code]);
        }
      }
      await api(`/entities/${entityCode}/records`, token, {
        method: 'POST',
        body: JSON.stringify({ data }),
      });
      setForm({});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.entityPage.createRecordFailed);
    }
  }

  async function remove(record: RecordItem) {
    setError(null);
    try {
      await api(`/entities/${entityCode}/records/${record.id}`, token, { method: 'DELETE' });
      setRecords((current) => current.filter((item) => item.id !== record.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t.entityPage.deleteRecordFailed);
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">2TO / EOS · {role}</p>
          <h1>{metadata?.definition.name ?? entityCode}</h1>
          <p className="muted">{entityCode}</p>
        </div>
        <div className="actions">
          <div className="pill">
            {metadata ? `v${metadata.version} · ${t.entityPage.published}` : t.entityPage.loadingMetadata}
          </div>
          <button className="secondary" onClick={onBack}>
            {t.entityPage.entities}
          </button>
          <button className="secondary" onClick={onLogout}>
            {t.entityPage.signOut}
          </button>
        </div>
      </header>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {metadata && (
        <section className="card">
          <h2>{t.entityPage.newRecordTitle}</h2>
          <div className="grid">
            {fields.map((field) => (
              <label key={field.code}>
                <span>
                  {field.label ?? field.code}
                  {field.required ? ' *' : ''}
                </span>
                {field.type === 'boolean' ? (
                  <input
                    type="checkbox"
                    checked={Boolean(form[field.code])}
                    onChange={(e) => setField(field, e.target.checked)}
                  />
                ) : field.type === 'relation' ? (
                  <RelationField
                    token={token}
                    field={field}
                    value={String(form[field.code] ?? '')}
                    onChange={(value) => setField(field, value)}
                  />
                ) : (
                  <input
                    type={
                      field.type === 'integer' || field.type === 'decimal'
                        ? 'number'
                        : field.type === 'date'
                          ? 'date'
                          : 'text'
                    }
                    value={String(form[field.code] ?? '')}
                    onChange={(e) => setField(field, e.target.value)}
                  />
                )}
              </label>
            ))}
          </div>
          {allowed('create') && (
            <button disabled={busy || fields.length === 0} onClick={() => void create()}>
              {t.entityPage.createRecord}
            </button>
          )}
        </section>
      )}
      {metadata && (
        <section className="card">
          <div className="section-head">
            <h2>{t.entityPage.recordsLabel}</h2>
            <button className="secondary" onClick={() => void load()}>
              {t.entityPage.refresh}
            </button>
          </div>
          {records.length === 0 ? (
            <p className="muted">{t.entityPage.noRecordsYet}</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t.entityPage.id}</th>
                    {fields.map((field) => (
                      <th key={field.code}>{field.label ?? field.code}</th>
                    ))}
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
                    <tr key={record.id}>
                      <td>{record.id.slice(0, 8)}…</td>
                      {fields.map((field) => (
                        <td key={field.code}>{String(record.data[field.code] ?? '')}</td>
                      ))}
                      <td>
                        {allowed('delete') && (
                          <button className="danger" onClick={() => void remove(record)}>
                            {t.entityPage.delete}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
