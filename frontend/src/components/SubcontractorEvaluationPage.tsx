import { FormEvent, useEffect, useMemo, useState } from 'react';
import { FiCheckCircle, FiPlus } from 'react-icons/fi';
import { subcontractorEvaluationAPI, type Evaluation, type EvaluationField, type EvaluationMetadata } from '../services/subcontractorEvaluation';

type Props = { language: 'ar' | 'en' };

const labels = {
  ar: { title: 'تقييم مقاولي الباطن', subtitle: 'شريحة رأسية حقيقية مبنية على Metadata وتعمل عبر PostgreSQL والـworkflow والـaudit.', bootstrap: 'تهيئة الكيان', create: 'إنشاء تقييم', score: 'التقييم الكلي', empty: 'لا توجد تقييمات بعد.', submit: 'إرسال للمراجعة', approve: 'اعتماد', reject: 'رفض', draft: 'مسودة', submitted: 'قيد المراجعة', approved: 'معتمد', rejected: 'مرفوض', required: 'حقل مطلوب' },
  en: { title: 'Subcontractor Evaluation', subtitle: 'A real vertical slice across metadata, PostgreSQL, workflow and audit.', bootstrap: 'Initialize entity', create: 'Create evaluation', score: 'Total score', empty: 'No evaluations yet.', submit: 'Submit for review', approve: 'Approve', reject: 'Reject', draft: 'Draft', submitted: 'In review', approved: 'Approved', rejected: 'Rejected', required: 'Required field' },
};

const fieldLabels: Record<string, [string, string]> = {
  subcontractor: ['مقاول الباطن', 'Subcontractor'],
  project: ['المشروع', 'Project'],
  evaluation_date: ['تاريخ التقييم', 'Evaluation date'],
  quality_score: ['الجودة', 'Quality'],
  safety_score: ['السلامة', 'Safety'],
  delivery_score: ['الالتزام بالتسليم', 'Delivery'],
  notes: ['ملاحظات', 'Notes'],
};

export default function SubcontractorEvaluationPage({ language }: Props) {
  const t = labels[language];
  const [metadata, setMetadata] = useState<EvaluationMetadata | null>(null);
  const [items, setItems] = useState<Evaluation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState<Record<string, string | number>>({ evaluation_date: new Date().toISOString().slice(0, 10), quality_score: 80, safety_score: 80, delivery_score: 80, subcontractor: '', project: '', notes: '' });

  const statusLabel = { draft: t.draft, submitted: t.submitted, approved: t.approved, rejected: t.rejected };
  const editableFields = useMemo(() => (metadata?.fields || []).filter(field => !['total_score', 'status'].includes(field.name)), [metadata]);

  const load = async () => {
    try {
      const schema = await subcontractorEvaluationAPI.metadata();
      setMetadata(schema.data);
      const records = await subcontractorEvaluationAPI.list();
      setItems(records.data.data || []);
    } catch (err: any) {
      if (err?.response?.status !== 404) setError(err?.response?.data?.detail || 'Unable to load evaluations');
    }
  };

  useEffect(() => { load(); }, []);

  const initialize = async () => {
    setBusy(true); setError('');
    try { await subcontractorEvaluationAPI.bootstrap(); await load(); }
    catch (err: any) { setError(err?.response?.data?.detail || 'Initialization requires administrator permission.'); }
    finally { setBusy(false); }
  };

  const create = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      await subcontractorEvaluationAPI.create(form as any);
      await load();
      setForm({ ...form, subcontractor: '', project: '', notes: '' });
    } catch (err: any) { setError(err?.response?.data?.detail || 'Unable to create evaluation'); }
    finally { setBusy(false); }
  };

  const transition = async (item: Evaluation, status: Evaluation['data']['status']) => {
    setBusy(true); setError('');
    try { await subcontractorEvaluationAPI.transition(item.id, status, item.row_version); await load(); }
    catch (err: any) { setError(err?.response?.data?.detail || 'Workflow transition failed'); }
    finally { setBusy(false); }
  };

  const inputFor = (field: EvaluationField) => {
    const value = form[field.name] ?? '';
    const type = field.field_type === 'integer' || field.field_type === 'decimal' ? 'number' : field.field_type === 'date' ? 'date' : 'text';
    return <input required={field.required} type={type} min={type === 'number' ? 0 : undefined} max={type === 'number' ? 100 : undefined} placeholder={fieldLabels[field.name]?.[language === 'ar' ? 0 : 1] || field.name} aria-label={fieldLabels[field.name]?.[language === 'ar' ? 0 : 1] || field.name} value={value} onChange={event => setForm({ ...form, [field.name]: type === 'number' ? Number(event.target.value) : event.target.value })} />;
  };

  return <>
    <section className="eos-page-heading">
      <div><span className="eos-eyebrow">metadata vertical slice · v{metadata?.version || '—'}</span><h1>{t.title}</h1><p>{t.subtitle}</p></div>
      {!metadata && <button className="eos-primary-button" onClick={initialize} disabled={busy}><FiPlus /> {t.bootstrap}</button>}
    </section>
    {error && <article className="eos-card" role="alert" style={{ marginBottom: 16 }}>{error}</article>}
    {metadata && <section className="eos-card" style={{ marginBottom: 20 }}><form onSubmit={create} style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))' }}>
      {editableFields.map(field => <div key={field.name}>{inputFor(field)}{field.required && <small>{t.required}</small>}</div>)}
      <button className="eos-primary-button" type="submit" disabled={busy} style={{ justifySelf: 'start' }}><FiPlus /> {t.create}</button>
    </form></section>}
    <section className="eos-card"><div className="eos-card-heading"><div><h2>{t.title}</h2><span>{items.length}</span></div></div>
      {items.length ? <div className="eos-task-list">{items.map(item => <div className="eos-task" key={item.id}>
        <div><strong>{item.data.subcontractor} · {item.data.project}</strong><small>{t.score}: {item.data.total_score}/100 · {item.data.evaluation_date}</small></div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}><span>{statusLabel[item.data.status]}</span>{item.data.status === 'draft' && <button className="eos-ghost-button" disabled={busy} onClick={() => transition(item, 'submitted')}>{t.submit}</button>}{item.data.status === 'submitted' && <><button className="eos-ghost-button" disabled={busy} onClick={() => transition(item, 'approved')}><FiCheckCircle /> {t.approve}</button><button className="eos-ghost-button" disabled={busy} onClick={() => transition(item, 'rejected')}>{t.reject}</button></>}</div>
      </div>)}</div> : <p>{t.empty}</p>}
    </section>
  </>;
}
