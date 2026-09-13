import { useState } from 'react';
import { api } from '../api';
import type { FieldType, Metadata, FormField } from '../types';

interface MetadataStudioProps {
  token: string;
  defaultCode: string;
  onCreated: (code: string) => void;
}

export function MetadataStudio({ token, defaultCode, onCreated }: MetadataStudioProps) {
  const [code, setCode] = useState(defaultCode || 'new_entity');
  const [name, setName] = useState('New Entity');
  const [fields, setFields] = useState<FormField[]>([{ code: 'name', type: 'text', required: true, label: 'Name' }]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function updateField(index: number, patch: Partial<FormField>) {
    setFields((current) => current.map((field, position) => (position === index ? { ...field, ...patch } : field)));
  }

  async function publish() {
    setError(null);
    setMessage(null);
    try {
      const created = await api<Metadata>('/metadata/entities', token, {
        method: 'POST',
        body: JSON.stringify({ code, name, fields: fields.map((field) => ({ ...field, nullable: false })) }),
      });
      await api(`/metadata/entities/${created.definition.code}/publish`, token, { method: 'POST' });
      setMessage(`Published ${created.definition.code} v${created.version}.`);
      onCreated(created.definition.code);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to publish metadata');
    }
  }

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <p className="eyebrow">Metadata Studio</p>
          <h2>Define an entity</h2>
        </div>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      {message && <div className="success" role="status">{message}</div>}
      <div className="grid">
        <label>
          <span>Entity code</span>
          <input value={code} onChange={(e) => setCode(e.target.value)} />
        </label>
        <label>
          <span>Display name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>
      <div className="field-list">
        {fields.map((field, index) => (
          <div className="field-row" key={`${index}-${field.code}`}>
            <input value={field.code} onChange={(e) => updateField(index, { code: e.target.value })} aria-label="Field code" />
            <select value={field.type} onChange={(e) => updateField(index, { type: e.target.value as FieldType })} aria-label="Field type">
              <option value="text">Text</option>
              <option value="integer">Integer</option>
              <option value="decimal">Decimal</option>
              <option value="boolean">Boolean</option>
              <option value="date">Date</option>
              <option value="uuid">UUID</option>
              <option value="relation">Relation</option>
            </select>
            <input value={field.label} onChange={(e) => updateField(index, { label: e.target.value })} aria-label="Field label" />
            {field.type === 'relation' && (
              <input
                value={field.target_entity ?? ''}
                onChange={(e) => updateField(index, { target_entity: e.target.value })}
                placeholder="Target entity"
                aria-label="Relation target"
              />
            )}
            <label className="inline-check">
              <input type="checkbox" checked={field.required} onChange={(e) => updateField(index, { required: e.target.checked })} /> Required
            </label>
            <button className="danger" onClick={() => setFields((current) => current.filter((_, position) => position !== index))}>
              Remove
            </button>
          </div>
        ))}
      </div>
      <div className="actions">
        <button
          className="secondary"
          onClick={() =>
            setFields((current) => [
              ...current,
              { code: `field_${current.length + 1}`, type: 'text', required: false, label: `Field ${current.length + 1}` },
            ])
          }
        >
          Add field
        </button>
        <button disabled={!code || !name || fields.length === 0} onClick={() => void publish()}>
          Publish entity
        </button>
      </div>
    </section>
  );
}
