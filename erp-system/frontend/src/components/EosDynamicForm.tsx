import { FormEvent, useEffect, useState } from 'react';
import { FiCheck, FiX } from 'react-icons/fi';
import { dynamicAPI } from '../services/dynamic';

type Props = { entityCode: string; language: 'ar' | 'en'; onClose: () => void };
type Field = { name: string; label?: string; widget?: string; input_type?: string; required?: boolean; readonly?: boolean; hidden?: boolean; relation?: { entity_code: string; display_field: string } };

export default function EosDynamicForm({ entityCode, language, onClose }: Props) {
  const [fields, setFields] = useState<Field[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    dynamicAPI.formSchema(entityCode).then((response) => setFields(response.data.data?.fields || [])).catch(() => setError(language === 'ar' ? 'تعذر تحميل تعريف النموذج.' : 'Unable to load the form schema.')).finally(() => setLoading(false));
  }, [entityCode, language]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true); setError('');
    try {
      await dynamicAPI.createRecord(entityCode, values);
      setSaved(true);
    } catch {
      setError(language === 'ar' ? 'تعذر حفظ السجل. تحقق من الصلاحيات وبيانات الشركة.' : 'The record could not be saved. Check permissions and tenant data.');
    } finally { setSaving(false); }
  };

  if (saved) return <div className="eos-modal-backdrop"><section className="eos-modal eos-success"><div className="eos-success-icon"><FiCheck /></div><h2>{language === 'ar' ? 'تم الحفظ' : 'Saved'}</h2><button className="eos-primary-button" onClick={onClose}>{language === 'ar' ? 'إغلاق' : 'Close'}</button></section></div>;
  return <div className="eos-modal-backdrop"><section className="eos-modal" role="dialog" aria-modal="true" aria-labelledby="eos-form-title"><div className="eos-modal-heading"><div><span className="eos-eyebrow">{entityCode}</span><h2 id="eos-form-title">{language === 'ar' ? 'سجل جديد' : 'New record'}</h2></div><button className="eos-icon-button" onClick={onClose} aria-label={language === 'ar' ? 'إغلاق' : 'Close'}><FiX /></button></div>{loading ? <div className="eos-grid-state">{language === 'ar' ? 'جاري تحميل النموذج…' : 'Loading form…'}</div> : <form onSubmit={submit}><div className="eos-form-grid">{fields.filter((field) => !field.hidden).map((field) => <label key={field.name} className="eos-form-field"><span>{language === 'ar' ? field.label || field.name : field.label || field.name}{field.required && ' *'}</span>{field.widget === 'textarea' ? <textarea required={field.required} readOnly={field.readonly} value={String(values[field.name] ?? '')} onChange={(e) => setValues({ ...values, [field.name]: e.target.value })} /> : field.widget === 'checkbox' ? <input type="checkbox" checked={Boolean(values[field.name])} disabled={field.readonly} onChange={(e) => setValues({ ...values, [field.name]: e.target.checked })} /> : field.widget === 'select' ? <select required={field.required} disabled={field.readonly} value={String(values[field.name] ?? '')} onChange={(e) => setValues({ ...values, [field.name]: e.target.value })}><option value="">—</option></select> : <input type={field.input_type === 'number' ? 'number' : field.input_type === 'email' ? 'email' : 'text'} required={field.required} readOnly={field.readonly} value={String(values[field.name] ?? '')} onChange={(e) => setValues({ ...values, [field.name]: e.target.value })} />}</label>)}</div>{error && <div className="eos-form-error" role="alert">{error}</div>}<div className="eos-modal-actions"><button type="button" className="eos-ghost-button" onClick={onClose}>{language === 'ar' ? 'إلغاء' : 'Cancel'}</button><button type="submit" className="eos-primary-button" disabled={saving}>{saving ? (language === 'ar' ? 'جاري الحفظ…' : 'Saving…') : (language === 'ar' ? 'حفظ' : 'Save')}</button></div></form>}</section></div>;
}
