import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { FiActivity, FiArrowRight, FiBarChart2, FiBell, FiBox, FiChevronDown, FiFileText, FiGlobe, FiHome, FiLogOut, FiMenu, FiPlus, FiSearch, FiSettings, FiShield, FiUsers } from 'react-icons/fi';
import EosDataGrid from './components/EosDataGrid';
import EosDynamicForm from './components/EosDynamicForm';
import EosOnboardingWizard from './components/EosOnboardingWizard';
import { authAPI, invoicesAPI, ordersAPI, reportsAPI } from './services/api';
import './styles/eos-app.css';

type Language = 'ar' | 'en';
type Translation = { home:string;customers:string;inventory:string;sales:string;reports:string;settings:string;search:string;welcome:string;subtitle:string;revenue:string;orders:string;receivables:string;tasks:string;newCustomer:string;viewAll:string;active:string;pending:string;onboarding:string;connected:string;switchLanguage:string };
const translations: Record<Language, Translation> = { ar:{home:'الرئيسية',customers:'العملاء',inventory:'المخزون',sales:'المبيعات',reports:'التقارير',settings:'الإعدادات',search:'بحث سريع',welcome:'مرحباً بك في EOS',subtitle:'منصة أعمال ذكية تبني مساحة العمل من طبيعة نشاطك.',revenue:'إيرادات الشهر',orders:'الفواتير',receivables:'المستحقات',tasks:'تنبيهات تحتاج انتباهك',newCustomer:'عميل جديد',viewAll:'عرض الكل',active:'نشط',pending:'قيد المراجعة',onboarding:'ابدأ بناء نظامك',connected:'متصل',switchLanguage:'English'}, en:{home:'Home',customers:'Customers',inventory:'Inventory',sales:'Sales',reports:'Reports',settings:'Settings',search:'Quick search',welcome:'Welcome to EOS',subtitle:'An intelligent business platform that builds your workspace around your business.',revenue:'Monthly revenue',orders:'Invoices',receivables:'Receivables',tasks:'Alerts needing attention',newCustomer:'New customer',viewAll:'View all',active:'Active',pending:'In review',onboarding:'Build your ERP',connected:'Connected',switchLanguage:'العربية'} };

type SessionUser = { id?:string; email?:string; tenant_id?:string; roles?:string[]; mfa_verified?:boolean };

function hasStoredSession() {
  return typeof localStorage !== 'undefined' && Boolean(localStorage.getItem('access_token'));
}

function readApiError(error: any, fallback: string) {
  return error?.response?.data?.detail?.error?.message || error?.response?.data?.detail || error?.message || fallback;
}

function isMfaRequired(error: any) {
  const message = String(error?.response?.data?.detail?.error?.message || error?.response?.data?.detail || '');
  return error?.response?.status === 401 && /MFA verification required/i.test(message);
}

function LoginScreen({ language, onLanguageChange, onLogin, onMfaRequired }: { language: Language; onLanguageChange: () => void; onLogin: (user: SessionUser) => void; onMfaRequired: () => void }) {
  const ar = language === 'ar';
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password) { setError(ar ? 'أدخل البريد الإلكتروني وكلمة المرور.' : 'Enter your email and password.'); return; }
    setBusy(true); setError('');
    try {
      await authAPI.login(email.trim(), password);
      try {
        const me = await authAPI.getCurrentUser(); onLogin(me.data?.data || { email: email.trim() });
      } catch (err) {
        if (isMfaRequired(err)) { onMfaRequired(); return; }
        throw err;
      }
    } catch (err) {
      setError(readApiError(err, ar ? 'تعذر تسجيل الدخول. تحقق من البيانات وحاول مرة أخرى.' : 'Unable to sign in. Check your credentials and try again.'));
    } finally { setBusy(false); }
  };
  return <div className="eos-auth-shell" dir={ar ? 'rtl' : 'ltr'}>
    <section className="eos-auth-card eos-card">
      <div className="eos-brand eos-auth-brand"><span className="eos-logo">E</span><span>EOS</span></div>
      <span className="eos-eyebrow">EOS DBP</span><h1>{ar ? 'تسجيل الدخول' : 'Sign in'}</h1>
      <p>{ar ? 'ادخل إلى مساحة عملك الآمنة.' : 'Access your secure business workspace.'}</p>
      <form onSubmit={submit} className="eos-auth-form">
        <label>{ar ? 'البريد الإلكتروني' : 'Email'}<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label>{ar ? 'كلمة المرور' : 'Password'}<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {error && <div className="eos-auth-error" role="alert">{error}</div>}
        <button className="eos-primary-button eos-auth-submit" disabled={busy}>{busy ? (ar ? 'جارٍ التحقق…' : 'Signing in…') : (ar ? 'دخول' : 'Sign in')} <FiArrowRight/></button>
      </form>
      <button className="eos-language eos-auth-language" onClick={onLanguageChange}><FiGlobe/> {ar ? 'English' : 'العربية'}</button>
    </section>
  </div>;
}

function MfaScreen({ language, onLanguageChange, onVerified, onCancel }: { language: Language; onLanguageChange: () => void; onVerified: (user: SessionUser) => void; onCancel: () => void }) {
  const ar = language === 'ar'; const [code,setCode]=useState(''); const [recovery,setRecovery]=useState(false); const [busy,setBusy]=useState(false); const [error,setError]=useState('');
  const submit = async (event: FormEvent) => { event.preventDefault(); if (!code.trim()) { setError(ar?'أدخل رمز التحقق.':'Enter the verification code.'); return; } setBusy(true); setError(''); try { if (recovery) await authAPI.verifyRecoveryCode(code.trim()); else await authAPI.verify2FA(code.trim()); const me=await authAPI.getCurrentUser(); onVerified(me.data?.data || {}); } catch (err) { setError(readApiError(err,ar?'رمز التحقق غير صالح أو انتهت المحاولة.':'The verification code is invalid or the challenge expired.')); } finally { setBusy(false); } };
  return <div className="eos-auth-shell" dir={ar?'rtl':'ltr'}>
    <section className="eos-auth-card eos-card">
      <div className="eos-brand eos-auth-brand"><span className="eos-logo"><FiShield/></span><span>EOS</span></div>
      <span className="eos-eyebrow">MFA</span><h1>{ar?'التحقق بخطوتين':'Two-factor verification'}</h1>
      <p>{recovery ? (ar?'أدخل أحد رموز الاسترداد المحفوظة.':'Enter one of your saved recovery codes.') : (ar?'أدخل رمز TOTP من تطبيق المصادقة.':'Enter the TOTP code from your authenticator app.')}</p>
      <form onSubmit={submit} className="eos-auth-form">
        <label>{recovery ? (ar?'رمز الاسترداد':'Recovery code') : (ar?'رمز المصادقة':'Authentication code')}<input inputMode={recovery?'text':'numeric'} autoComplete="one-time-code" maxLength={8} value={code} onChange={(e)=>setCode(e.target.value)} required /></label>
        {error&&<div className="eos-auth-error" role="alert">{error}</div>}
        <button className="eos-primary-button eos-auth-submit" disabled={busy}>{busy?(ar?'جارٍ التحقق…':'Verifying…'):(ar?'تحقق':'Verify')} <FiArrowRight/></button>
      </form>
      <div className="eos-auth-options">
        <button className="eos-ghost-button" onClick={()=>{setRecovery(!recovery);setCode('');setError('');}}>{recovery?(ar?'استخدام رمز التطبيق':'Use authenticator code'):(ar?'استخدام رمز استرداد':'Use recovery code')}</button>
        <button className="eos-ghost-button" onClick={onCancel}>{ar?'تسجيل خروج':'Sign out'}</button>
      </div>
      <button className="eos-language eos-auth-language" onClick={onLanguageChange}><FiGlobe/> {ar?'English':'العربية'}</button>
    </section>
  </div>;
}

export default function App() {
  const [lang,setLang]=useState<Language>('ar'); const [page,setPage]=useState('home'); const [builder,setBuilder]=useState(false); const [sessionChecked,setSessionChecked]=useState(false); const [mfaRequired,setMfaRequired]=useState(false); const [user,setUser]=useState<SessionUser|null>(null); const t=translations[lang];
  useEffect(()=>{ let alive=true; const handleExpired=()=>{if(alive){setUser(null);setMfaRequired(false);}}; window.addEventListener('eos:auth-expired',handleExpired); if(!hasStoredSession()){setSessionChecked(true);return()=>{alive=false;window.removeEventListener('eos:auth-expired',handleExpired);};} authAPI.getCurrentUser().then(r=>{if(alive){setUser(r.data?.data||null);setMfaRequired(false);}}).catch(err=>{if(alive){if(isMfaRequired(err))setMfaRequired(true);else setUser(null);}}).finally(()=>{if(alive)setSessionChecked(true);}); return()=>{alive=false;window.removeEventListener('eos:auth-expired',handleExpired);};},[]);
  const onLogin=(next:SessionUser)=>{setMfaRequired(false);setUser(next);};
  const logout=async()=>{try{await authAPI.logout();}finally{setUser(null);setMfaRequired(false);setPage('home');setBuilder(false);}};
  if(!sessionChecked)return <div className="eos-auth-shell"><div className="eos-card eos-auth-card"><div className="eos-brand eos-auth-brand"><span className="eos-logo">E</span><span>EOS</span></div><p>{lang==='ar'?'جارٍ التحقق من الجلسة…':'Checking session…'}</p></div></div>;
  if(mfaRequired)return <MfaScreen language={lang} onLanguageChange={()=>setLang(lang==='ar'?'en':'ar')} onVerified={onLogin} onCancel={logout}/>;
  if(!user)return <LoginScreen language={lang} onLanguageChange={()=>setLang(lang==='ar'?'en':'ar')} onLogin={onLogin} onMfaRequired={()=>setMfaRequired(true)}/>;
  const nav=[[t.home,'home',FiHome],[t.customers,'customers',FiUsers],[t.inventory,'inventory',FiBox],[t.sales,'sales',FiFileText],[t.reports,'reports',FiBarChart2],[t.settings,'settings',FiSettings]] as const;
  return <div className="eos-app" dir={lang==='ar'?'rtl':'ltr'}><aside className="eos-sidebar"><div className="eos-brand"><span className="eos-logo">E</span><span>EOS</span></div><button className="eos-create" onClick={()=>setBuilder(true)}><FiPlus/><span>{t.onboarding}</span></button><nav>{nav.map(([label,key,Icon])=><button key={key} className={`eos-nav-item ${page===key?'is-active':''}`} onClick={()=>{setBuilder(false);setPage(key);}}><Icon/><span>{label}</span></button>)}</nav><div className="eos-sidebar-footer"><span className="eos-status-dot"/>{t.connected}</div></aside><main className="eos-main"><header className="eos-topbar"><button className="eos-icon-button eos-mobile-menu" aria-label={lang==='ar'?'القائمة':'Menu'}><FiMenu/></button><div className="eos-search"><FiSearch/><input aria-label={t.search} placeholder={t.search}/></div><div className="eos-top-actions"><button className="eos-language" onClick={()=>setLang(lang==='ar'?'en':'ar')}><FiGlobe/> {t.switchLanguage}</button><button className="eos-icon-button" aria-label={lang==='ar'?'الإشعارات':'Notifications'}><FiBell/></button><div className="eos-avatar" title={user.email||'EOS'}>{(user.email||'EOS').slice(0,2).toUpperCase()}</div><button className="eos-icon-button" aria-label={lang==='ar'?'تسجيل الخروج':'Log out'} onClick={logout}><FiLogOut/></button></div></header><div className="eos-content">{builder?<EosOnboardingWizard language={lang} onBack={()=>setBuilder(false)} onComplete={()=>setBuilder(false)}/>:page==='customers'?<Customers t={t} language={lang}/>:page==='inventory'?<Inventory t={t} language={lang}/>:page==='sales'?<Sales language={lang}/>:page==='reports'?<Reports t={t} language={lang}/>:page==='settings'?<Settings t={t}/>:<Dashboard t={t} onBuild={()=>setBuilder(true)} language={lang}/>}</div></main></div>;
}

function Dashboard({t,onBuild,language}:{t:Translation;onBuild:()=>void;language:Language}){const [summary,setSummary]=useState<any>(null);const [sales,setSales]=useState<any>(null);const [inventory,setInventory]=useState<any>(null);const [loadError,setLoadError]=useState('');useEffect(()=>{let alive=true;Promise.all([reportsAPI.profitAndLoss(),reportsAPI.sales(),reportsAPI.inventory()]).then(([p,s,i])=>{if(alive){setSummary(p.data?.data);setSales(s.data?.data);setInventory(i.data?.data);setLoadError('');}}).catch((error)=>{if(alive)setLoadError(readApiError(error,language==='ar'?'تعذر تحميل بيانات لوحة التحكم.':'Dashboard data could not be loaded.'));});return()=>{alive=false;};},[language]);const revenue=summary?.revenue??0;const invoices=sales?.daily?.reduce((n:number,x:any)=>n+Number(x.count||0),0)??0;const receivables=summary?.receivables??0;const cards=[[t.revenue,formatMoney(revenue),summary?`${summary.gross_margin??0}%`:t.connected,FiActivity],[t.orders,String(invoices),sales?`${sales.top_customers?.length??0} ${language==='ar'?'عملاء نشطون':'active customers'}`:t.connected,FiBox],[t.receivables,formatMoney(receivables),`${inventory?.total_items??0} ${language==='ar'?'صنف':'items'}`,FiBarChart2]] as const;return <><section className="eos-page-heading"><div><span className="eos-eyebrow">EOS DBP</span><h1>{t.welcome}</h1><p>{t.subtitle}</p></div><button className="eos-primary-button" onClick={onBuild}>{t.onboarding}<FiArrowRight/></button></section>{loadError&&<div className="eos-auth-error" role="status">{loadError}</div>}<section className="eos-kpi-grid">{cards.map(([label,value,delta,Icon])=><article className="eos-card eos-kpi" key={label}><div className="eos-kpi-icon"><Icon/></div><span>{label}</span><strong>{value}</strong><small>{delta}</small></article>)}</section><section className="eos-dashboard-grid"><article className="eos-card eos-chart-card"><div className="eos-card-heading"><div><h2>{language==='ar'?'الأداء':'Performance'}</h2><span>{language==='ar'?'بيانات من محرك التقارير':'Reporting engine data'}</span></div><button className="eos-ghost-button">{language==='ar'?'هذا الشهر':'This month'} <FiChevronDown/></button></div><div className="eos-bars" aria-label={language==='ar'?'اتجاه المبيعات':'Sales trend'}>{(sales?.daily?.slice(-12)||[]).map((x:any,i:number)=><span key={i} style={{height:`${Math.max(8,Math.min(100,Number(x.amount||0)/(Math.max(...(sales?.daily||[]).map((d:any)=>Number(d.amount||0)),1))*100))}%`}}/>)}{!sales?.daily?.length&&<span style={{height:'8%'}}/>}</div></article><article className="eos-card eos-chart-card"><div className="eos-card-heading"><div><h2>{t.tasks}</h2><span>{language==='ar'?'مؤشرات من النظام':'System indicators'}</span></div></div><div className="eos-task-list"><div className="eos-task"><span className="eos-task-check">✓</span><div><strong>{language==='ar'?'المستحقات قيد المتابعة':'Receivables are being monitored'}</strong><small>{t.active}</small></div></div><div className="eos-task"><span className="eos-task-check">✓</span><div><strong>{language==='ar'?'المخزون منخفض حسب مستوى إعادة الطلب':'Inventory reorder levels checked'}</strong><small>{inventory?.low_stock_items??0} {language==='ar'?'أصناف':'items'}</small></div></div><div className="eos-task"><span className="eos-task-check">✓</span><div><strong>{language==='ar'?'صافي الربح':'Gross profit'}</strong><small>{formatMoney(summary?.gross_profit??0)}</small></div></div></div></article></section></>}
function Customers({t,language}:{t:Translation;language:Language}){const [formOpen,setFormOpen]=useState(false);return <>{formOpen&&<EosDynamicForm entityCode="customers" language={language} onClose={()=>setFormOpen(false)}/>}<section className="eos-page-heading"><div><span className="eos-eyebrow">customers</span><h1>{t.customers}</h1><p>{language==='ar'?'إدارة العملاء من خلال طبقة Metadata والصلاحيات الخلفية.':'Customer workspace backed by metadata and tenant permissions.'}</p></div><button className="eos-primary-button" onClick={()=>setFormOpen(true)}><FiPlus/> {t.newCustomer}</button></section><EosDataGrid entityCode="customers" language={language}/></>}
function Inventory({t,language}:{t:Translation;language:Language}){return <><section className="eos-page-heading"><div><span className="eos-eyebrow">inventory</span><h1>{t.inventory}</h1><p>{language==='ar'?'المخزون الفعلي مع البحث والتصفية.':'Live inventory with search and filtering.'}</p></div></section><EosDataGrid entityCode="items" language={language}/></>}
function Sales({language}:{language:Language}){const [orders,setOrders]=useState<any[]>([]);const [invoices,setInvoices]=useState<any[]>([]);const [busy,setBusy]=useState('');const [error,setError]=useState('');const ar=language==='ar';const load=useCallback(()=>Promise.all([ordersAPI.getAll(),invoicesAPI.getAll()]).then(([o,i])=>{setOrders(o.data?.data||[]);setInvoices(i.data?.data||[]);setError('');}).catch((e)=>setError(readApiError(e,ar?'تعذر تحميل دورة المبيعات.':'Sales data could not be loaded.'))),[ar]);useEffect(()=>{void load();},[load]);const issue=async(id:string)=>{setBusy(id);setError('');try{await invoicesAPI.issue(id);await load();}catch(e){setError(readApiError(e,ar?'تعذر إصدار الفاتورة.':'Unable to issue invoice.'));}finally{setBusy('');}};return <><section className="eos-page-heading"><div><span className="eos-eyebrow">sales</span><h1>{ar?'دورة المبيعات':'Sales cycle'}</h1><p>{ar?'أوامر البيع والفواتير والتحصيل مع ترحيل محاسبي مزدوج.':'Orders, invoices and collections with double-entry accounting.'}</p></div></section>{error&&<div className="eos-auth-error" role="status">{error}</div>}<section className="eos-dashboard-grid"><article className="eos-card eos-chart-card"><div className="eos-card-heading"><div><h2>{ar?'أوامر البيع':'Sales orders'}</h2><span>{orders.length} {ar?'مستند':'documents'}</span></div></div>{orders.length?<div className="eos-task-list">{orders.slice(0,8).map((o:any)=><div className="eos-task" key={o.id}><div><strong>{o.order_number||o.id}</strong><small>{o.customer_name||'—'} · {formatMoney(o.total_amount)} {o.currency_code||''}</small></div><span>{o.status}</span></div>)}</div>:<p>{ar?'لا توجد أوامر بيع بعد.':'No sales orders yet.'}</p>}</article><article className="eos-card eos-chart-card"><div className="eos-card-heading"><div><h2>{ar?'الفواتير':'Invoices'}</h2><span>{invoices.length} {ar?'فاتورة':'invoices'}</span></div></div>{invoices.length?<div className="eos-task-list">{invoices.slice(0,8).map((i:any)=><div className="eos-task" key={i.id}><div><strong>{i.invoice_number||i.id}</strong><small>{i.customer_name||'—'} · {formatMoney(i.total_amount+(i.tax_amount||0))}</small></div>{i.status==='draft'?<button className="eos-ghost-button" disabled={busy===i.id} onClick={()=>issue(i.id)}>{busy===i.id?(ar?'جارٍ…':'Issuing…'):(ar?'إصدار':'Issue')}</button>:<span>{i.status}</span>}</div>)}</div>:<p>{ar?'لا توجد فواتير بعد.':'No invoices yet.'}</p>}</article></section></>}
function Reports({t,language}:{t:Translation;language:Language}){const [data,setData]=useState<any>(null);const [error,setError]=useState('');useEffect(()=>{reportsAPI.profitAndLoss().then(r=>setData(r.data?.data)).catch((e)=>setError(readApiError(e,language==='ar'?'تعذر تحميل التقرير.':'Report data could not be loaded.')));},[language]);return <><section className="eos-page-heading"><div><span className="eos-eyebrow">reports</span><h1>{t.reports}</h1><p>{language==='ar'?'تقارير مالية وتشغيلية من محرك التقارير الخلفي.':'Financial and operational reports from the backend reporting engine.'}</p></div></section>{error&&<div className="eos-auth-error" role="status">{error}</div>}<section className="eos-kpi-grid"><article className="eos-card eos-kpi"><span>{t.revenue}</span><strong>{formatMoney(data?.revenue)}</strong></article><article className="eos-card eos-kpi"><span>{language==='ar'?'تكلفة المبيعات':'Cost of goods sold'}</span><strong>{formatMoney(data?.cost_of_goods)}</strong></article><article className="eos-card eos-kpi"><span>{language==='ar'?'مجمل الربح':'Gross profit'}</span><strong>{formatMoney(data?.gross_profit)}</strong></article></section></>}
function Settings({t}:{t:Translation}){return <section className="eos-empty-state eos-card"><FiSettings/><h1>{t.settings}</h1><p>EOS configuration is metadata-driven and tenant-scoped.</p></section>}
function formatMoney(value:unknown){return new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value||0))}
