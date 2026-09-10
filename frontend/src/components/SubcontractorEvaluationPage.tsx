import { FormEvent, useEffect, useState } from 'react';
import { FiCheckCircle, FiPlus } from 'react-icons/fi';
import { subcontractorEvaluationAPI, type Evaluation } from '../services/subcontractorEvaluation';

type Props = { language: 'ar' | 'en' };

const labels = {
  ar: { title: 'تقييم مقاولي الباطن', subtitle: 'شريحة رأسية حقيقية مبنية على Metadata وتعمل عبر PostgreSQL والـworkflow والـaudit.', subcontractor: 'مقاول الباطن', project: 'المشروع', date: 'تاريخ التقييم', quality: 'الجودة', safety: 'السلامة', delivery: 'الالتزام بالتسليم', notes: 'ملاحظات', create: 'إنشاء تقييم', bootstrap: 'تهيئة الكيان', status: 'الحالة', score: 'التقييم الكلي', empty: 'لا توجد تقييمات بعد.', submit: 'إرسال للمراجعة', approve: 'اعتماد', reject: 'رفض', draft: 'مسودة', submitted: 'قيد المراجعة', approved: 'معتمد', rejected: 'مرفوض' },
  en: { title: 'Subcontractor Evaluation', subtitle: 'A real vertical slice across metadata, PostgreSQL, workflow and audit.', subcontractor: 'Subcontractor', project: 'Project', date: 'Evaluation date', quality: 'Quality', safety: 'Safety', delivery: 'Delivery', notes: 'Notes', create: 'Create evaluation', bootstrap: 'Initialize entity', status: 'Status', score: 'Total score', empty: 'No evaluations yet.', submit: 'Submit for review', approve: 'Approve', reject: 'Reject', draft: 'Draft', submitted: 'In review', approved: 'Approved', rejected: 'Rejected' },
};

export default function SubcontractorEvaluationPage({ language }: Props) {
  const t = labels[language];
  const [items, setItems] = useState<Evaluation[]>([]);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ subcontractor: '', project: '', evaluation_date: new Date().toISOString().slice(0, 10), quality_score: 80, safety_score: 80, delivery_score: 80, notes: '' });

  const load = () => subcontractorEvaluationAPI.list().then((response) => setItems(response.data.data || [])).catch((err) => setError(err?.response?.data?.detail || 'Unable to load evaluations'));

  useEffect(() => { load(); }, []);

  const initialize = async () => {
    setBusy(true); setError('');
    try { await subcontractorEvaluationAPI.bootstrap(); setBootstrapped(true); await load(); }
    catch (err: any) { setError(err?.response?.data?.detail || 'Initialization requires administrator permission.'); }
    finally { setBusy(false); }
  };

  const create = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await subcontractorEvaluationAPI.create(form); await load(); setForm({ ...form, subcontractor: '', project: '', notes: '' }); }
    catch (err: any) { setError(err?.response?.data?.detail || 'Unable to create evaluation'); }
    finally { setBusy(false); }
  };

  const transition = async (item: Evaluation, status: Evaluation['data']['status']) => {
    setBusy(true); setError('');
    try { await subcontractorEvaluationAPI.transition(item.id, status, item.row_version); await load(); }
    catch (err: any) { setError(err?.response?.data?.detail || 'Workflow transition failed'); }
    finally { setBusy(false); }
  };

  return <>
    <section className="eos-page-heading">
      <div><span className="eos-eyebrow">metadata vertical slice</span><h1>{t.title}</h1><p>{t.subtitle}</p></div>
      {!bootstrapped && <button className="eos-primary-button" onClick={initialize} disabled={busy}><FiPlus /> {t.bootstrap}</button>}
    </section>

    {error && <article className="eos-card" role="alert" style={{ marginBottom: 16 }}>{error}</article>}

    <section className="eos-card" style={{ marginBottom: 20 }}>
      <form onSubmit={create} style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))' }}>
        <input required placeholder={t.subcontractor} value={form.subcontractor} onChange={e => setForm({ ...form, subcontractor: e.target.value })} />
        <input required placeholder={t.project} value={form.project} onChange={e => setForm({ ...form, project: e.target.value })} />
        <input required type="date" aria-label={t.date} value={form.evaluation_date} onChange={e => setForm({ ...form, evaluation_date: e.target.value })} />
        <input required type="number" min="0" max="100" aria-label={t.quality} placeholder={t.quality} value={form.quality_score} onChange={e => setForm({ ...form, quality_score: Number(e.target.value) })} />
        <input required type="number" min="0" max="100" aria-label={t.safety} placeholder={t.safety} value={form.safety_score} onChange={e => setForm({ ...form, safety_score: Number(e.target.value) })} />
        <input required type="number" min="0" max="100" aria-label={t.delivery} placeholder={t.delivery} value={form.delivery_score} onChange={e => setForm({ ...form, delivery_score: Number(e.target.value) })} />
        <input placeholder={t.notes} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} style={{ gridColumn: '1 / -1' }} />
        <button className="eos-primary-button" type="submit" disabled={busy || !bootstrapped} style={{ justifySelf: 'start' }}><FiPlus /> {t.create}</button>
      </form>
    </section>

    <section className="eos-card"><div className="eos-card-heading"><div><h2>{t.title}</h2><span>{items.length}</span></div></div>
      {items.length ? <div className="eos-task-list">{items.map(item => <div className="eos-task" key={item.id}>
        <div><strong>{item.data.subcontractor} · {item.data.project}</strong><small>{t.score}: {item.data.total_score}/100 · {t.date}: {item.data.evaluation_date}</small></div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}><span>{t[item.data.status]}</span>{item.data.status === 'draft' && <button className="eos-ghost-button" disabled={busy} onClick={() => transition(item, 'submitted')}>{t.submit}</button>}{item.data.status === 'submitted' && <><button className="eos-ghost-button" disabled={busy} onClick={() => transition(item, 'approved')}><FiCheckCircle /> {t.approve}</button><button className="eos-ghost-button" disabled={busy} onClick={() => transition(item, 'rejected')}>{t.reject}</button></>}</div>
      </div>)}</div> : <p>{t.empty}</p>}
    </section>
  </>;
}
