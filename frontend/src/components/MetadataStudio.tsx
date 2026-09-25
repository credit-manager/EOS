import { useState } from 'react';
import { api } from '../api';
import { useI18n } from '../i18n';
import type { FieldType, Metadata, FormField } from '../types';

interface MetadataStudioProps {
  token: string;
  defaultCode: string;
  onCreated: (code: string) => void;
}

export function MetadataStudio({ token, defaultCode, onCreated }: MetadataStudioProps) {
  const { t } = useI18n();
  const [code, setCode] = useState(defaultCode || 'new_entity');
  const [name, setName] = useState(t.metadataStudio.newEntity);
  const [fields, setFields] = useState<FormField[]>([
    { code: 'name', type: 'text', required: true, label: t.metadataStudio.defaultFieldLabel },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function updateField(index: number, patch: Partial<FormField>) {
    setFields((current) =>
      current.map((field, position) => (position === index ? { ...field, ...patch } : field))
    );
  }

  async function publish() {
    setError(null);
    setMessage(null);
    try {
      const created = await api<Metadata>('/metadata/entities', token, {
        method: 'POST',
        body: JSON.stringify({
          code,
          name,
          fields: fields.map((field) => ({ ...field, nullable: false })),
        }),
      });
      await api(`/metadata/entities/${created.definition.code}/publish`, token, { method: 'POST' });
      setMessage(`${t.metadataStudio.published} ${created.definition.code} v${created.version}.`);
      onCreated(created.definition.code);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.metadataStudio.unableToPublish);
    }
  }

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <p className="eyebrow">{t.metadataStudio.title}</p>
          <h2>{t.metadataStudio.subtitle}</h2>
        </div>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="success" role="status">
          {message}
        </div>
      )}
      <div className="grid">
        <label>
          <span>{t.metadataStudio.entityCode}</span>
          <input value={code} onChange={(e) => setCode(e.target.value)} />
        </label>
        <label>
          <span>{t.metadataStudio.displayName}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>
      <div className="field-list">
        {fields.map((field, index) => (
          <div className="field-row" key={`${index}-${field.code}`}>
            <input
              value={field.code}
              onChange={(e) => updateField(index, { code: e.target.value })}
              aria-label={t.metadataStudio.fieldCode}
            />
            <select
              value={field.type}
              onChange={(e) => updateField(index, { type: e.target.value as FieldType })}
              aria-label={t.metadataStudio.fieldType}
            >
              <option value="text">{t.metadataStudio.text}</option>
              <option value="integer">{t.metadataStudio.integer}</option>
              <option value="decimal">{t.metadataStudio.decimal}</option>
              <option value="boolean">{t.metadataStudio.boolean}</option>
              <option value="date">{t.metadataStudio.date}</option>
              <option value="uuid">{t.metadataStudio.uuid}</option>
              <option value="relation">{t.metadataStudio.relation}</option>
            </select>
            <input
              value={field.label}
              onChange={(e) => updateField(index, { label: e.target.value })}
              aria-label={t.metadataStudio.fieldLabel}
            />
            {field.type === 'relation' && (
              <input
                value={field.target_entity ?? ''}
                onChange={(e) => updateField(index, { target_entity: e.target.value })}
                placeholder={t.metadataStudio.targetEntity}
                aria-label={t.metadataStudio.relationTarget}
              />
            )}
            <label className="inline-check">
              <input
                type="checkbox"
                checked={field.required}
                onChange={(e) => updateField(index, { required: e.target.checked })}
              />{' '}
              {t.metadataStudio.required}
            </label>
            <button
              className="danger"
              onClick={() =>
                setFields((current) => current.filter((_, position) => position !== index))
              }
            >
              {t.metadataStudio.remove}
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
              {
                code: `field_${current.length + 1}`,
                type: 'text',
                required: false,
                label: `${t.metadataStudio.field} ${current.length + 1}`,
              },
            ])
          }
        >
          {t.metadataStudio.addField}
        </button>
        <button disabled={!code || !name || fields.length === 0} onClick={() => void publish()}>
          {t.metadataStudio.publishEntity}
        </button>
      </div>
    </section>
  );
}
