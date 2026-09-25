import { useState, useEffect } from 'react';
import { api } from '../api';
import type { MetadataSummary } from '../types';
import { MetadataStudio } from './MetadataStudio';

interface CatalogPageProps {
  token: string;
  role: string;
  defaultEntity: string;
  onSelect: (code: string) => void;
  onLogout: () => void;
  onCreate: () => void;
}

export function CatalogPage({
  token,
  role,
  defaultEntity,
  onSelect,
  onLogout,
  onCreate,
}: CatalogPageProps) {
  const [entities, setEntities] = useState<MetadataSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setEntities(await api<MetadataSummary[]>('/metadata/entities', token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load entity catalog');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">2TO / EOS</p>
          <h1>Entity workspace</h1>
          <p className="muted">
            Choose a published metadata entity. The UI is generated from its definition.
          </p>
        </div>
        <button className="secondary" onClick={onLogout}>
          Sign out
        </button>
      </header>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {role === 'admin' && (
        <MetadataStudio token={token} defaultCode={defaultEntity} onCreated={onSelect} />
      )}
      <section className="card">
        <div className="section-head">
          <h2>Published entities</h2>
          <div className="actions">
            <span className="pill">{entities.length} available</span>
            {role === 'admin' && <button onClick={onCreate}>New entity</button>}
            <button className="secondary" onClick={() => void load()}>
              Refresh
            </button>
          </div>
        </div>
        {busy ? (
          <p className="muted">Loading catalog…</p>
        ) : entities.length === 0 ? (
          <p className="muted">No published entities exist yet.</p>
        ) : (
          <div className="catalog-grid">
            {entities.map((entity) => (
              <button
                className="entity-card"
                key={entity.code}
                onClick={() => onSelect(entity.code)}
              >
                <strong>{entity.name}</strong>
                <span>{entity.code}</span>
                <small>
                  v{entity.version} · {entity.field_count} fields
                </small>
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
