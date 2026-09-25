import { useState, useEffect } from 'react';
import { api } from '../api';
import type { MetadataSummary } from '../types';
import { MetadataStudio } from './MetadataStudio';
import { useI18n } from '../i18n';

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
  const { t } = useI18n();
  const [entities, setEntities] = useState<MetadataSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setEntities(await api<MetadataSummary[]>('/metadata/entities', token));
    } catch (err) {
      setError(err instanceof Error ? err.message : t.catalogPage.loadError);
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
          <p className="eyebrow">{t.catalogPage.eyebrow}</p>
          <h1>{t.catalogPage.title}</h1>
          <p className="muted">{t.catalogPage.subtitle}</p>
        </div>
        <button className="secondary" onClick={onLogout}>
          {t.catalogPage.signOut}
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
          <h2>{t.catalogPage.publishedEntities}</h2>
          <div className="actions">
            <span className="pill">
              {entities.length} {t.catalogPage.available}
            </span>
            {role === 'admin' && <button onClick={onCreate}>{t.catalogPage.newEntity}</button>}
            <button className="secondary" onClick={() => void load()}>
              {t.catalogPage.refresh}
            </button>
          </div>
        </div>
        {busy ? (
          <p className="muted">{t.catalogPage.loading}</p>
        ) : entities.length === 0 ? (
          <p className="muted">{t.catalogPage.noEntities}</p>
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
                  v{entity.version} · {entity.field_count} {t.catalogPage.fields}
                </small>
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
