import { useEffect, useMemo, useState } from 'react';
import { FiArrowLeft, FiArrowRight, FiCheckCircle, FiLoader } from 'react-icons/fi';
import { onboardingAPI } from '../services/api';

type Language = 'ar' | 'en';
type Props = { language: Language; onBack: () => void; onComplete: () => void };
type Industry = { id: string; industry_code: string; industry_name: string; industry_name_ar?: string; description?: string; default_modules?: string[] };
type Module = { id: string; module_code: string; module_name: string; module_name_ar?: string; description?: string; required_modules?: string[]; default_enabled?: boolean };
type Status = { status: string; current_step?: string; progress_percent?: number; steps_completed?: string[]; industry_code?: string; plan_id?: string; company_name?: string; company_name_ar?: string; selected_modules?: string[] };

const STEPS = ['industry_selection','plan_selection','company_creation','template_application','module_configuration','admin_setup','activation'];
const labels: Record<Language, Record<string,string>> = { ar:{industry_selection:'النشاط',plan_selection:'الخطة',company_creation:'الشركة',template_application:'القالب',module_configuration:'الوحدات',admin_setup:'المسؤول',activation:'التفعيل'}, en:{industry_selection:'Industry',plan_selection:'Plan',company_creation:'Company',template_application:'Template',module_configuration:'Modules',admin_setup:'Admin',activation:'Activation'} };

export default function EosOnboardingWizard({ language, onBack, onComplete }: Props) {
  const ar = language === 'ar';
  const [status,setStatus] = useState<Status|null>(null);
  const [industries,setIndustries] = useState<Industry[]>([]);
  const [modules,setModules] = useState<Module[]>([]);
  const [industry,setIndustry] = useState('');
  const [plan,setPlan] = useState('trial');
  const [company,setCompany] = useState('');
  const [companyAr,setCompanyAr] = useState('');
  const [selected,setSelected] = useState<string[]>([]);
  const [loading,setLoading] = useState(true);
  const [saving,setSaving] = useState(false);
  const [error,setError] = useState('');

  const currentIndex = Math.max(0, STEPS.indexOf(status?.current_step || 'industry_selection'));
  const currentStep = STEPS[currentIndex];
  const title = labels[language][currentStep];

  useEffect(() => { (async()=>{ try { const [s,i,m] = await Promise.all([onboardingAPI.status().catch(()=>null), onboardingAPI.industries(), onboardingAPI.modules()]); const sd=s?.data?.data; setStatus(sd); setIndustries(i.data?.data || []); setModules(m.data?.data || []); if(sd?.industry_code)setIndustry(sd.industry_code); if(sd?.company_name)setCompany(sd.company_name); if(sd?.company_name_ar)setCompanyAr(sd.company_name_ar); if(sd?.selected_modules?.length)setSelected(sd.selected_modules); } catch(e:any){ setError(e?.response?.data?.detail?.error?.message || (ar?'تعذر تحميل بيانات البناء':'Unable to load builder data')); } finally {setLoading(false);} })(); }, [ar]);

  const availableModules = useMemo(()=>modules, [modules]);
  const canContinue = currentStep==='industry_selection' ? !!industry : currentStep==='company_creation' ? !!company.trim() : currentStep==='module_configuration' ? selected.length>0 : true;

  const saveStep = async () => {
    if(!canContinue) return; setSaving(true); setError('');
    try {
      if(!status) await onboardingAPI.start();
      let data: Record<string,unknown> = {};
      if(currentStep==='industry_selection') data={industry_code:industry};
      if(currentStep==='plan_selection') data={plan_id:plan};
      if(currentStep==='company_creation') data={company_name:company.trim(),company_name_ar:companyAr.trim()};
      if(currentStep==='template_application') data={industry_code:industry};
      if(currentStep==='module_configuration') data={modules:selected};
      if(currentStep==='admin_setup') data={};
      if(currentStep==='activation') data={};
      const r=await onboardingAPI.completeStep(currentStep,data); const next=r.data?.data; setStatus((p)=>({...p,...next,current_step:next.current_step,status:next.status,steps_completed:next.steps_completed}));
      if(currentStep==='activation' || next?.status==='completed') onComplete();
    } catch(e:any){ setError(e?.response?.data?.detail?.error?.message || (ar?'تعذر حفظ المرحلة':'Unable to save this step')); } finally {setSaving(false);} 
  };

  if(loading) return <section className="eos-onboarding eos-success"><FiLoader className="eos-spin"/><p>{ar?'جاري تحميل مسار البناء…':'Loading your workspace build…'}</p></section>;
  return <section className="eos-onboarding"><button className="eos-back-button" onClick={onBack}><FiArrowLeft/> {ar?'رجوع':'Back'}</button><div className="eos-onboarding-inner"><span className="eos-eyebrow">EOS BUSINESS BUILDER</span><div className="eos-progress"><div><strong>{ar?'بناء نظامك':'Build your ERP'}</strong><span>{status?.progress_percent ?? 0}%</span></div><div className="eos-progress-track"><span style={{width:`${status?.progress_percent ?? 0}%`}}/></div></div><h1>{title}</h1><p>{ar?'أكمل المرحلة الحالية وسيتم حفظها في مساحة شركتك.':'Complete the current stage and it will be persisted for your company.'}</p>{currentStep==='industry_selection' && <div className="eos-choice-grid">{industries.map(x=><button key={x.id} className={industry===x.industry_code?'is-selected':''} onClick={()=>{setIndustry(x.industry_code); if(x.default_modules?.length)setSelected(x.default_modules)}}><strong>{ar?(x.industry_name_ar||x.industry_name):x.industry_name}</strong><small>{x.description}</small></button>)}</div>}{currentStep==='plan_selection' && <div className="eos-choice-grid"><button className={plan==='trial'?'is-selected':''} onClick={()=>setPlan('trial')}><strong>{ar?'تجربة':'Trial'}</strong><small>{ar?'ابدأ قبل الالتزام بخطة مدفوعة.':'Start before committing to a paid plan.'}</small></button><button className={plan==='professional'?'is-selected':''} onClick={()=>setPlan('professional')}><strong>{ar?'احترافي':'Professional'}</strong><small>{ar?'للنمو والفرق المتوسطة.':'For growing teams.'}</small></button><button className={plan==='enterprise'?'is-selected':''} onClick={()=>setPlan('enterprise')}><strong>{ar?'مؤسسي':'Enterprise'}</strong><small>{ar?'للمؤسسات والعمليات المتقدمة.':'For enterprise operations.'}</small></button></div>}{currentStep==='company_creation' && <div className="eos-form-grid"><label className="eos-form-field"><span>{ar?'اسم الشركة':'Company name'} *</span><input value={company} onChange={e=>setCompany(e.target.value)}/></label><label className="eos-form-field"><span>{ar?'اسم الشركة بالعربية':'Arabic company name'}</span><input dir="rtl" value={companyAr} onChange={e=>setCompanyAr(e.target.value)}/></label></div>}{currentStep==='template_application' && <div className="eos-builder-note">{ar?'سيتم تطبيق إعدادات وقواعد الحسابات والوحدات الافتراضية للنشاط المحدد.':'The selected industry template will provide default settings, modules and accounting configuration.'}</div>}{currentStep==='module_configuration' && <div className="eos-choice-grid">{availableModules.map(x=>{const code=x.module_code; const checked=selected.includes(code); return <button key={x.id} className={checked?'is-selected':''} onClick={()=>setSelected(v=>checked?v.filter(i=>i!==code):[...v,code])}><strong>{ar?(x.module_name_ar||x.module_name):x.module_name}</strong><small>{x.description}</small>{x.required_modules?.length?<small>{ar?'يتطلب: ':'Requires: '}{x.required_modules.join(', ')}</small>:null}</button>})}</div>}{currentStep==='admin_setup' && <div className="eos-builder-note">{ar?'سيتم استخدام المستخدم الإداري الحالي كمسؤول مساحة الشركة.':'Your authenticated administrator will own the company workspace.'}</div>}{currentStep==='activation' && <div className="eos-builder-note"><FiCheckCircle/> {ar?'راجع إعداداتك ثم فعّل مساحة العمل.':'Review your configuration and activate the workspace.'}</div>}{error&&<div className="eos-form-error" role="alert">{error}</div>}<div className="eos-modal-actions"><span>{currentIndex+1} / {STEPS.length}</span><button className="eos-primary-button" disabled={!canContinue||saving} onClick={saveStep}>{saving?(ar?'جاري الحفظ…':'Saving…'):(currentStep==='activation'?(ar?'تفعيل':'Activate'):(ar?'متابعة':'Continue'))}<FiArrowRight/></button></div><div className="eos-stepper">{STEPS.map((s,i)=><span key={s} className={i<=currentIndex?'is-done':''}>{i+1}. {labels[language][s]}</span>)}</div></div></section>;
}
