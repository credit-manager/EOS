import { useMemo, useState } from 'react';
import { FiActivity, FiArrowRight, FiBarChart2, FiBell, FiBox, FiCheckCircle, FiChevronDown, FiGlobe, FiHome, FiMenu, FiPlus, FiSearch, FiSettings, FiUsers } from 'react-icons/fi';
import { customersAPI } from './services/api';
import type { EosEntitySchema, EosFieldSchema } from './design-system';
import './styles/eos-app.css';

type Language = 'ar' | 'en';

const translations = {
  ar: { home: 'الرئيسية', workspace: 'مساحة العمل', customers: 'العملاء', inventory: 'المخزون', reports: 'التقارير', settings: 'الإعدادات', search: 'بحث سريع', welcome: 'مرحباً بك في EOS', subtitle: 'منصة أعمال ذكية تبني مساحة العمل من طبيعة نشاطك.', revenue: 'إيرادات الشهر', orders: 'الطلبات', receivables: 'المستحقات', tasks: 'مهام تحتاج انتباهك', newCustomer: 'عميل جديد', viewAll: 'عرض الكل', status: 'الحالة', customer: 'العميل', amount: 'القيمة', active: 'نشط', pending: 'قيد المراجعة', onboarding: 'ابدأ بناء نظامك', business: 'ما طبيعة نشاطك؟', generate: 'إنشاء مساحة العمل', generated: 'تم تجهيز مساحة العمل', back: 'رجوع', demo: 'بيانات تجريبية', switchLanguage: 'English' },
  en: { home: 'Home', workspace: 'Workspace', customers: 'Customers', inventory: 'Inventory', reports: 'Reports', settings: 'Settings', search: 'Quick search', welcome: 'Welcome to EOS', subtitle: 'An intelligent business platform that builds your workspace around your business.', revenue: 'Monthly revenue', orders: 'Orders', receivables: 'Receivables', tasks: 'Tasks needing attention', newCustomer: 'New customer', viewAll: 'View all', status: 'Status', customer: 'Customer', amount: 'Amount', active: 'Active', pending: 'In review', onboarding: 'Build your ERP', business: 'What does your business do?', generate: 'Generate workspace', generated: 'Workspace ready', back: 'Back', demo: 'Demo data', switchLanguage: 'العربية' },
} as const;

const customerFields: EosFieldSchema[] = [
  { key: 'name', label: 'Customer name', type: 'text', ui: { component: 'text', required: true, width: 6 } },
  { key: 'email', label: 'Email', type: 'email', ui: { component: 'email', width: 6 } },
  { key: 'phone', label: 'Phone', type: 'text', ui: { component: 'tel', width: 6 } },
  { key: 'status', label: 'Status', type: 'select', ui: { component: 'select', width: 6 }, options: [{ label: 'Active', value: 'active' }, { label: 'In review', value: 'pending' }] },
];
const customerSchema: EosEntitySchema = { key: 'customers', label: 'Customers', fields: customerFields, capabilities: { create: true, update: true, delete: true, export: true } };

function App() {
  const [lang, setLang] = useState<Language>('ar');
  const [page, setPage] = useState('home');
  const [onboarding, setOnboarding] = useState(false);
  const [business, setBusiness] = useState('');
  const [ready, setReady] = useState(false);
  const t = translations[lang];
  const dir = lang === 'ar' ? 'rtl' : 'ltr';
  const nav = useMemo(() => [
    [t.home, 'home', FiHome], [t.customers, 'customers', FiUsers], [t.inventory, 'inventory', FiBox], [t.reports, 'reports', FiBarChart2], [t.settings, 'settings', FiSettings],
  ] as const, [t]);

  return <div className="eos-app" dir={dir}>
    <aside className="eos-sidebar">
      <div className="eos-brand"><span className="eos-logo">E</span><span>EOS</span></div>
      <button className="eos-create" onClick={() => setOnboarding(true)}><FiPlus /> {t.newCustomer}</button>
      <nav aria-label="Main navigation">{nav.map(([label, key, Icon]) => <button key={key} className={`eos-nav-item ${page === key ? 'is-active' : ''}`} onClick={() => setPage(key)}><Icon /> <span>{label}</span></button>)}</nav>
      <div className="eos-sidebar-footer"><span className="eos-status-dot" /> {t.demo}</div>
    </aside>

    <main className="eos-main">
      <header className="eos-topbar">
        <button className="eos-icon-button eos-mobile-menu" aria-label="Menu"><FiMenu /></button>
        <div className="eos-search"><FiSearch /><input aria-label={t.search} placeholder={t.search} /></div>
        <div className="eos-top-actions">
          <button className="eos-language" onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}><FiGlobe /> {t.switchLanguage}</button>
          <button className="eos-icon-button" aria-label="Notifications"><FiBell /><span className="eos-notification-dot" /></button>
          <div className="eos-avatar" aria-label="User profile">CM</div>
        </div>
      </header>

      <div className="eos-content">
        {onboarding ? <Onboarding t={t} business={business} setBusiness={setBusiness} ready={ready} setReady={setReady} onBack={() => setOnboarding(false)} /> : page === 'customers' ? <CustomerWorkspace t={t} /> : <Dashboard t={t} onBuild={() => setOnboarding(true)} />}
      </div>
    </main>
  </div>;
}

function Dashboard({ t, onBuild }: { t: typeof translations.ar; onBuild: () => void }) {
  const kpis = [[t.revenue, '€128,420', '+12.8%', FiActivity], [t.orders, '1,284', '+8.4%', FiBox], [t.receivables, '€42,760', '-3.2%', FiBarChart2]] as const;
  return <>
    <section className="eos-page-heading"><div><span className="eos-eyebrow">EOS DBP</span><h1>{t.welcome}</h1><p>{t.subtitle}</p></div><button className="eos-primary-button" onClick={onBuild}>{t.onboarding}<FiArrowRight /></button></section>
    <section className="eos-kpi-grid">{kpis.map(([label, value, delta, Icon]) => <article className="eos-card eos-kpi" key={label}><div className="eos-kpi-icon"><Icon /></div><span>{label}</span><strong>{value}</strong><small>{delta}</small></article>)}</section>
    <section className="eos-dashboard-grid">
      <article className="eos-card eos-chart-card"><div className="eos-card-heading"><div><h2>Performance</h2><span>Last 6 months</span></div><button className="eos-ghost-button">Monthly <FiChevronDown /></button></div><div className="eos-bars" aria-label="Revenue trend">{[44, 58, 52, 72, 66, 88, 79, 96, 84, 100, 92, 108].map((h, i) => <span key={i} style={{ height: `${h}%` }} />)}</div></article>
      <article className="eos-card"><div className="eos-card-heading"><div><h2>{t.tasks}</h2><span>4 items</span></div><button className="eos-ghost-button">{t.viewAll}</button></div><div className="eos-task-list"><Task label="Approve purchase order #1042" status={t.pending} /><Task label="Invoice INV-2088 is overdue" status="Action" /><Task label="Stock level below threshold" status={t.pending} /><Task label="Monthly close ready" status={t.active} /></div></article>
    </section>
  </>;
}

function Task({ label, status }: { label: string; status: string }) { return <div className="eos-task"><span className="eos-task-check"><FiCheckCircle /></span><div><strong>{label}</strong><small>{status}</small></div></div>; }

function CustomerWorkspace({ t }: { t: typeof translations.ar }) {
  const rows = [{ name: 'Acme Industries', email: 'finance@acme.example', amount: '€24,500', status: t.active }, { name: 'Northstar Group', email: 'ops@northstar.example', amount: '€18,200', status: t.active }, { name: 'Cedar Trading', email: 'hello@cedar.example', amount: '€9,840', status: t.pending }, { name: 'Atlas Construction', email: 'accounts@atlas.example', amount: '€7,620', status: t.active }];
  return <><section className="eos-page-heading"><div><span className="eos-eyebrow">{customerSchema.key}</span><h1>{t.customers}</h1><p>Metadata-driven entity workspace.</p></div><button className="eos-primary-button"><FiPlus /> {t.newCustomer}</button></section><div className="eos-card eos-table-card"><div className="eos-table-toolbar"><div className="eos-search eos-table-search"><FiSearch /><input placeholder={t.search} /></div><button className="eos-ghost-button">Filters <FiChevronDown /></button></div><div className="eos-table-wrap"><table><thead><tr><th>{t.customer}</th><th>Email</th><th>{t.amount}</th><th>{t.status}</th></tr></thead><tbody>{rows.map(r => <tr key={r.name}><td><strong>{r.name}</strong></td><td>{r.email}</td><td>{r.amount}</td><td><span className={`eos-pill ${r.status === t.active ? 'success' : 'warning'}`}>{r.status}</span></td></tr>)}</tbody></table></div><div className="eos-table-footer">Showing 1–4 of 4</div></div></>;
}

function Onboarding({ t, business, setBusiness, ready, setReady, onBack }: { t: typeof translations.ar; business: string; setBusiness: (v: string) => void; ready: boolean; setReady: (v: boolean) => void; onBack: () => void }) {
  if (ready) return <section className="eos-onboarding eos-success"><div className="eos-success-icon"><FiCheckCircle /></div><span className="eos-eyebrow">EOS</span><h1>{t.generated}</h1><p>Your workspace includes Sales, Finance, Inventory and a role-based dashboard.</p><div className="eos-generation-grid"><span>✓ Finance</span><span>✓ Sales</span><span>✓ Inventory</span><span>✓ Customers</span></div><button className="eos-primary-button" onClick={onBack}>{t.home}<FiArrowRight /></button></section>;
  return <section className="eos-onboarding"><button className="eos-back-button" onClick={onBack}>← {t.back}</button><div className="eos-onboarding-inner"><span className="eos-eyebrow">EOS BUSINESS BUILDER</span><h1>{t.onboarding}</h1><p>{t.subtitle}</p><label htmlFor="business">{t.business}</label><textarea id="business" value={business} onChange={e => setBusiness(e.target.value)} placeholder={langPlaceholder(t)} rows={5} /><div className="eos-suggestions"><button onClick={() => setBusiness('Real estate development and property management')}>Real estate</button><button onClick={() => setBusiness('Construction company with projects, procurement and payroll')}>Construction</button><button onClick={() => setBusiness('Trading and distribution company')}>Trading</button></div><button className="eos-primary-button eos-generate" disabled={!business.trim()} onClick={() => setReady(true)}>{t.generate}<FiArrowRight /></button><div className="eos-stepper"><span className="is-done">1. Business</span><span>2. Clarify</span><span>3. Generate</span><span>4. Launch</span></div></div></section>;
}

function langPlaceholder(t: typeof translations.ar) { return t === translations.ar ? 'مثال: شركة تطوير عقاري تشتري الأراضي وتبني وتبيع الوحدات...' : 'Example: a construction company managing projects, procurement, payroll and finance...'; }

export default App;
