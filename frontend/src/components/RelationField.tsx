import { useState, useEffect } from 'react';
import { api } from '../api';
import type { Field, LookupItem } from '../types';

interface RelationFieldProps {
  token: string;
  field: Field;
  value: string;
  onChange: (value: string) => void;
}

export function RelationField({ token, field, value, onChange }: RelationFieldProps) {
  const [items, setItems] = useState<LookupItem[]>([]);
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(async () => {
      if (!field.target_entity) return;
      setBusy(true);
      setError(null);
      try {
        const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}&limit=25` : '?limit=25';
        const data = await api<LookupItem[]>(`/entities/${field.target_entity}/lookup${suffix}`, token);
        if (active) setItems(data);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load choices');
      } finally {
        if (active) setBusy(false);
      }
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [field.target_entity, query, token]);

  return (
    <div className="relation-field">
      {error && <div className="error" role="alert">{error}</div>}
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search related records"
        aria-label={`${field.label ?? field.code} search`}
      />
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={busy} aria-label={field.label ?? field.code}>
        <option value="">{busy ? 'Loading…' : 'Select a record'}</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>{item.label}</option>
        ))}
      </select>
      {value && <small className="muted">Selected: {value.slice(0, 8)}…</small>}
    </div>
  );
}
