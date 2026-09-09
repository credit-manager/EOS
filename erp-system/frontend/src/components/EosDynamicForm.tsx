import { FormEvent, useEffect, useMemo, useState } from 'react';
import { FiCheck, FiX } from 'react-icons/fi';
import { dynamicAPI } from '../services/dynamic';

type Props = { entityCode: string; language: 'ar' | 'en'; onClose: () => void };
type Field = { name: string; label?: string; label_ar?: string; widget?: string; component?: string; input_type?: string; type?: string; required?: boolean; readonly?: boolean; hidden?: boolean; help?: string; width?: number; validation?: { min?: number; max?: number; min_length?: number; max_length?: number; pattern?: string }; relation?: { entity_code: string; display_field: string } };
type LookupOption = { value: string; label: string };

const getWidget = (field: Field) => field.widget || field.component || (field.type === 'boolean' ? 'checkbox' : field.type === 'relation' ? 'select' : field.type || 'text');

export default function EosDynamicForm({ entityCode, language, onClose }: Props) {
  const [fields, setFields] = useState<Field[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [options, setOptions] = useState<Record<string, LookupOption[]>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let alive = true;
    dynamicAPI.formSchema(entityCode).then((response) => {
      if (alive) setFields((response.data.data?.fields || []) as Field[]);
    }).catch(() => alive && setError(language === 'ar' ? 'تعذر تحميل تعريف النموذج.' : 'Unable to load the form schema.')).finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [entityCode, language]);

  const relationFields = useMemo(() => fields.filter((field) => Boolean(field.relation)), [fields]);

  useEffect(() => {
    let alive = true;
    relationFields.forEach(async (field) => {
      if (!field.relation) return;
      try {
        const response = await dynamicAPI.lookup(entityCode, field.name, '', 50);
        const raw = (response.data as { data?: unknown }).data;
        const list = Array.isArray(raw) ? raw : [];
        const mapped = list.map((item) => {
          const value = typeof item === 'object' && item !== null ? (item as Record<string, unknown>).id ?? (item as Record<string, unknown>).value : item;
          const label = typeof item === 'object' && item !== null ? (item as Record<string, unknown>)[field.relation!.display_field] ?? (item as Record<string, unknown>).label ?? value : item;
          return { value: String(value ?? ''), label: String(label ?? '') };
        }).filter((item) => item.value);
        if (alive) setOptions((current) => ({ ...current, [field.name]: mapped }));
      } catch { /* relation lookup is optional; the form remains usable */ }
    });
    return () => { alive = false; };
  }, [entityCode, relationFields]);

  const setValue = (name: string, value: unknown) => setValues((current) => ({ ...current, [name]: value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError('');
    try { await dynamicAPI.createRecord(entityCode, values); setSaved(true); }
    catch { setError(language === 'ar' ? 'تعذر حفظ السجل. تحقق من الصلاحيات وبيانات الشركة.' : 'The record could not be saved. Check permissions and tenant data.'); }
    finally { setSaving(false); }
  };

  if (saved) return <div className="eos-modal-backdrop"><section className="eos-modal eos-success"><div className="eos-success-icon"><FiCheck /></div><h2>{language === 'ar' ? 'تم الحفظ' : 'Saved'}</h2><button className="eos-primary-button" onClick={onClose}>{language === 'ar' ? 'إغلاق' : 'Close'}</button></section></div>;
  return <div className="eos-modal-backdrop"><section className="eos-modal" role="dialog" aria-modal="true" aria-labelledby="eos-form-title"><div className="eos-modal-heading"><div><span className="eos-eyebrow">{entityCode}</span><h2 id="eos-form-title">{language === 'ar' ? 'سجل جديد' : 'New record'}</h2></div><button className="eos-icon-button" onClick={onClose} aria-label={language === 'ar' ? 'إغلاق' : 'Close'}><FiX /></button></div>{loading ? <div className="eos-grid-state">{language === 'ar' ? 'جاري تحميل النموذج…' : 'Loading form…'}</div> : <form onSubmit={submit}><div className="eos-form-grid">{fields.filter((field) => !field.hidden).map((field) => { const widget = getWidget(field); const label = language === 'ar' ? field.label_ar || field.label || field.name : field.label || field.name; const validation = field.validation || {}; const common = { required: field.required, disabled: field.readonly, minLength: validation.min_length, maxLength: validation.max_length, min: validation.min, max: validation.max, pattern: validation.pattern };
        return <label key={field.name} className="eos-form-field" style={{ gridColumn: `span ${Math.min(Math.max(field.width || 6, 1), 12)}` }}><span>{label}{field.required && ' *'}</span>{field.help && <small>{field.help}</small>}{widget === 'textarea' ? <textarea {...common} readOnly={field.readonly} value={String(values[field.name] ?? '')} onChange={(e) => setValue(field.name, e.target.value)} /> : widget === 'checkbox' ? <input type="checkbox" checked={Boolean(values[field.name])} disabled={field.readonly} onChange={(e) => setValue(field.name, e.target.checked)} /> : widget === 'select' || field.relation ? <select {...common} value={String(values[field.name] ?? '')} onChange={(e) => setValue(field.name, e.target.value)}><option value="">—</option>{(options[field.name] || []).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select> : <input type={field.input_type === 'number' || widget === 'number' ? 'number' : field.input_type === 'email' || widget === 'email' ? 'email' : 'text'} {...common} readOnly={field.readonly} value={String(values[field.name] ?? '')} onChange={(e) => setValue(field.name, e.target.value)} />}</label>; })}</div>{error && <div className="eos-form-error" role="alert">{error}</div>}<div className="eos-modal-actions"><button type="button" className="eos-ghost-button" onClick={onClose}>{language === 'ar' ? 'إلغاء' : 'Cancel'}</button><button type="submit" className="eos-primary-button" disabled={saving}>{saving ? (language === 'ar' ? 'جاري الحفظ…' : 'Saving…') : (language === 'ar' ? 'حفظ' : 'Save')}</button></div></form>}</section></div>;
}
