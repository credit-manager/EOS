import { useMemo, useState } from 'react';

type Mode = 'business' | 'owner';
type Page =
  | 'overview' | 'business' | 'projects' | 'contracts' | 'procurement' | 'finance'
  | 'ai' | 'automation' | 'analytics' | 'graph' | 'documents'
  | 'owner-overview' | 'organizations' | 'users' | 'subscriptions' | 'security' | 'health';

const businessNav: Array<{id: Page; label: string; group?: string}> = [
  {id:'overview', label:'Command Center', group:'CORE'},
  {id:'business', label:'Business Workspace'},
  {id:'projects', label:'Projects'},
  {id:'contracts', label:'Contracts'},
  {id:'procurement', label:'Procurement'},
  {id:'finance', label:'Finance'},
  {id:'ai', label:'AI Workforce', group:'INTELLIGENCE'},
  {id:'automation', label:'Automation'},
  {id:'analytics', label:'Analytics'},
  {id:'graph', label:'Business Graph'},
  {id:'documents', label:'Documents', group:'PLATFORM'},
];

const ownerNav: Array<{id: Page; label: string; group?: string}> = [
  {id:'owner-overview', label:'Platform Command Center', group:'PLATFORM'},
  {id:'organizations', label:'Organizations'},
  {id:'users', label:'Users & Access'},
  {id:'subscriptions', label:'Subscriptions & Billing'},
  {id:'ai', label:'AI Control Center', group:'OPERATIONS'},
  {id:'security', label:'Security & Audit'},
  {id:'health', label:'System Health'},
];

const projects = [
  ['North Coast Logistics Hub','Construction','78%','$18.4M','On track'],
  ['Cairo Industrial Expansion','Industrial','61%','$11.7M','Attention'],
  ['Delta Water Infrastructure','Infrastructure','92%','$24.1M','On track'],
  ['New Capital Operations Center','Facilities','44%','$8.9M','On track'],
];

const modules = [
  ['Projects','24 active','Portfolio, delivery, cost and risk'],
  ['Contracts','118 active','Obligations, claims and exposure'],
  ['Procurement','$9.6M','Requests, sourcing and POs'],
  ['Finance','$42.8M','Revenue, cash and receivables'],
  ['AI Workforce','7 agents','Business-aware digital workers'],
  ['Automation','18 active','Rules, workflows and events'],
];

export default function DemoPage({onExit}:{onExit:()=>void}) {
  const [mode,setMode] = useState<Mode>('business');
  const [page,setPage] = useState<Page>('overview');
  const [query,setQuery] = useState('');
  const [notice,setNotice] = useState('');
  const [aiPrompt,setAiPrompt] = useState('What requires executive attention today?');
  const [aiAnswer,setAiAnswer] = useState('Three items require attention: one contract approval, a procurement variance on the steel package, and three receivables approaching due date.');

  const nav = mode === 'business' ? businessNav : ownerNav;
  const filteredNav = useMemo(() => nav.filter(x => !query || x.label.toLowerCase().includes(query.toLowerCase())), [nav,query]);
  const notify = (message:string) => { setNotice(message); window.setTimeout(() => setNotice(''), 2200); };
  const changeMode = (next:Mode) => { setMode(next); setPage(next === 'business' ? 'overview' : 'owner-overview'); setQuery(''); };

  return (
    <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
      <header className="sticky top-0 z-50 border-b border-slate-800 bg-[#0b1020] text-white">
        <div className="mx-auto flex h-[68px] max-w-[1600px] items-center gap-4 px-5 lg:px-7">
          <div className="flex min-w-[230px] items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-[11px] font-black text-slate-950">2TO</div>
            <div>
              <div className="text-sm font-bold tracking-tight">2TO EOS</div>
              <div className="text-[9px] uppercase tracking-[0.22em] text-slate-400">Business Operating System</div>
            </div>
          </div>
          <div className="hidden flex-1 md:block">
            <div className="mx-auto max-w-xl">
              <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-xs text-slate-400">
                <span className="text-slate-500">⌘</span>
                <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search anything or jump to a workspace…" className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500" />
                <kbd className="rounded border border-white/10 px-1.5 py-0.5 text-[9px]">K</kbd>
              </div>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-[10px] font-bold tracking-wide text-emerald-300 sm:inline-flex">DEMO ENVIRONMENT</span>
            <button onClick={()=>notify('Demo action — no live data was changed.')} className="hidden rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-white/10 lg:block">Help</button>
            <button onClick={onExit} className="rounded-lg bg-white px-3.5 py-2 text-xs font-bold text-slate-900 hover:bg-slate-100">Exit Demo</button>
          </div>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-68px)]">
        <aside className="hidden w-[270px] shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
          <div className="border-b border-slate-100 p-5">
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Environment</div>
            <button className="mt-3 flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-left">
              <span><b className="block text-sm">Nile Horizon Group</b><span className="text-[10px] text-slate-500">Enterprise demo tenant</span></span>
              <span className="text-slate-400">⌄</span>
            </button>
          </div>
          <div className="border-b border-slate-100 p-3">
            <div className="grid grid-cols-2 rounded-xl bg-slate-100 p-1">
              <button onClick={()=>changeMode('business')} className={`rounded-lg px-2 py-2 text-[11px] font-bold transition ${mode==='business'?'bg-white text-slate-900 shadow-sm':'text-slate-500'}`}>Business</button>
              <button onClick={()=>changeMode('owner')} className={`rounded-lg px-2 py-2 text-[11px] font-bold transition ${mode==='owner'?'bg-white text-slate-900 shadow-sm':'text-slate-500'}`}>Platform</button>
            </div>
          </div>
          <nav className="flex-1 overflow-y-auto p-3">
            {filteredNav.map((item,index) => (
              <div key={item.id}>
                {item.group && <div className="px-3 pb-2 pt-4 text-[9px] font-bold tracking-[0.18em] text-slate-400">{item.group}</div>}
                <button onClick={()=>setPage(item.id)} className={`group mb-1 flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-[13px] font-semibold transition ${page===item.id?'bg-slate-900 text-white shadow-sm':'text-slate-600 hover:bg-slate-50 hover:text-slate-950'}`}>
                  <span>{item.label}</span><span className={page===item.id?'text-white/50':'text-slate-300'}>›</span>
                </button>
              </div>
            ))}
          </nav>
          <div className="border-t border-slate-100 p-4">
            <div className="rounded-xl bg-slate-950 p-4 text-white">
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Product preview</div>
              <div className="mt-2 text-xs leading-5 text-slate-300">Explore the connected business model, AI workforce and operating workflows.</div>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <div className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex max-w-[1450px] items-center justify-between gap-4 px-5 py-5 lg:px-8">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{mode==='business'?'Nile Horizon Group':'2TO EOS Control Plane'}</div>
                <h1 className="mt-1 text-2xl font-bold tracking-tight">{nav.find(x=>x.id===page)?.label ?? 'Command Center'}</h1>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={()=>notify('Search opened')} className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 md:hidden">Search</button>
                <button onClick={()=>notify('Demo action — no live data was changed.')} className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-bold text-white hover:bg-slate-800">Create</button>
              </div>
            </div>
          </div>

          <div className="mx-auto max-w-[1450px] p-5 lg:p-8">
            {notice && <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-700">{notice}</div>}
            {mode==='business' && page==='overview' && <BusinessOverview onAction={notify}/>}
            {mode==='business' && page==='business' && <BusinessWorkspace/>}
            {mode==='business' && page==='projects' && <ProjectWorkspace/>}
            {mode==='business' && page==='contracts' && <ContractsWorkspace/>}
            {mode==='business' && page==='procurement' && <ProcurementWorkspace/>}
            {mode==='business' && page==='finance' && <FinanceWorkspace/>}
            {mode==='business' && page==='ai' && <AIWorkspace prompt={aiPrompt} setPrompt={setAiPrompt} answer={aiAnswer} ask={()=>{setAiAnswer('EOS connected projects, contracts, procurement and finance to identify the highest-impact executive actions.');notify('AI analysis completed.')}}/>}
            {mode==='business' && page==='automation' && <AutomationWorkspace onAction={notify}/>}
            {mode==='business' && page==='analytics' && <AnalyticsWorkspace/>}
            {mode==='business' && page==='graph' && <GraphWorkspace/>}
            {mode==='business' && page==='documents' && <DocumentsWorkspace/>}
            {mode==='owner' && page==='owner-overview' && <OwnerOverview/>}
            {mode==='owner' && page==='organizations' && <OwnerTable title="Organizations" subtitle="Tenant lifecycle and platform usage" rows={[['Nile Horizon Group','Enterprise','84 users','Healthy'],['Delta Infrastructure','Business','37 users','Healthy'],['Atlas Holdings','Enterprise','126 users','Review'],['Cairo Operations','Business','22 users','Healthy']]}/>}
            {mode==='owner' && page==='users' && <OwnerTable title="Users & Access" subtitle="Identity, roles and organization access" rows={[['Amr Hassan','Nile Horizon Group','Owner','Active'],['Mona Ali','Nile Horizon Group','Finance','Active'],['Omar Saleh','Delta Infrastructure','Admin','Active'],['Sara Nabil','Atlas Holdings','Manager','Review']]}/>}
            {mode==='owner' && page==='subscriptions' && <OwnerTable title="Subscriptions & Billing" subtitle="Commercial status across organizations" rows={[['Nile Horizon Group','Enterprise','Active','$4,800 / mo'],['Delta Infrastructure','Business','Active','$1,900 / mo'],['Atlas Holdings','Enterprise','Trial','$0 / mo'],['Cairo Operations','Business','Active','$1,200 / mo']]}/>}
            {mode==='owner' && page==='security' && <OwnerTable title="Security & Audit" subtitle="Platform-wide security signals" rows={[['Authentication','All regions','Healthy','2 min ago'],['Tenant isolation','All tenants','Healthy','5 min ago'],['Privileged access','4 events','Review','Today'],['Audit pipeline','98.9% processed','Healthy','1 min ago']]}/>}
            {mode==='owner' && page==='health' && <OwnerTable title="System Health" subtitle="Services, jobs and platform operations" rows={[['API Gateway','Operational','99.98%','42 ms'],['Workflow Engine','Operational','99.95%','18 ms'],['AI Runtime','Operational','99.91%','1.4 s'],['Background Jobs','Operational','99.97%','31 active']]}/>}
          </div>
        </main>
      </div>
    </div>
  );
}

function Section({eyebrow,title,children}:{eyebrow?:string;title:string;children:React.ReactNode}) {
  return <section className="space-y-4"><div><div className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{eyebrow}</div><h2 className="mt-1 text-lg font-bold tracking-tight">{title}</h2></div>{children}</section>;
}

function BusinessOverview({onAction}:{onAction:(m:string)=>void}) {
  const cards=[['Portfolio Value','$63.1M','+8.4%'],['Active Projects','24','3 need attention'],['Contract Exposure','$31.7M','6.2% at risk'],['Cash Position','$12.8M','+14.1%']];
  return <div className="space-y-8">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(c=><div key={c[0]} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_30px_rgba(15,23,42,.04)]"><div className="text-xs text-slate-500">{c[0]}</div><div className="mt-2 text-2xl font-bold tracking-tight">{c[1]}</div><div className="mt-2 text-[11px] font-semibold text-emerald-600">{c[2]}</div></div>)}</div>
    <div className="grid gap-5 xl:grid-cols-[1.45fr_.8fr]">
      <div className="rounded-2xl border border-slate-200 bg-white p-6"><div className="flex items-start justify-between"><div><h3 className="font-bold">Business performance</h3><p className="mt-1 text-xs text-slate-500">Portfolio value and operating momentum</p></div><span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[10px] font-bold text-slate-500">12 months</span></div><div className="mt-8 flex h-52 items-end gap-2">{[38,45,42,55,51,63,59,72,68,78,84,94].map((h,i)=><div key={i} className="flex-1 rounded-t bg-slate-900/90" style={{height:`${h}%`}}/>)}</div><div className="mt-3 flex justify-between text-[10px] text-slate-400"><span>Oct</span><span>Jan</span><span>Apr</span><span>Jul</span><span>Sep</span></div></div>
      <div className="rounded-2xl border border-slate-200 bg-white p-6"><h3 className="font-bold">AI executive brief</h3><p className="mt-1 text-xs text-slate-500">Prioritized from connected business signals</p><div className="mt-5 space-y-3">{[['Finance','3 receivables approach due date.'],['Procurement','Steel package is 6% above benchmark.'],['Contracts','CNT-2026-038 needs approval.'],['Projects','North Coast is ahead of plan.']].map(x=><button key={x[0]} onClick={()=>onAction(`Opened ${x[0]} insight`)} className="w-full rounded-xl border border-slate-100 bg-slate-50 p-3 text-left hover:border-slate-200 hover:bg-white"><div className="text-xs font-bold">{x[0]}</div><div className="mt-1 text-[11px] leading-5 text-slate-500">{x[1]}</div></button>)}</div></div>
    </div>
    <Section eyebrow="Operating system" title="Everything connected">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{modules.map(m=><div key={m[0]} className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-lg"><div className="flex items-center justify-between"><h3 className="font-bold">{m[0]}</h3><span className="text-[11px] font-bold text-slate-400">{m[1]}</span></div><p className="mt-2 text-xs leading-5 text-slate-500">{m[2]}</p><div className="mt-5 text-[11px] font-bold text-slate-900">Explore workspace →</div></div>)}</div>
    </Section>
  </div>;
}

function BusinessWorkspace(){return <Section eyebrow="Business" title="Business Workspace"><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{['Customers','Suppliers','Employees','Business Objects','Invoices','Purchase Orders','Documents','Locations'].map((x,i)=><div key={x} className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-sm font-bold">{String(i+1).padStart(2,'0')}</div><h3 className="mt-4 font-bold">{x}</h3><p className="mt-1 text-xs text-slate-500">{['286 records','94 active','412 members','18 object types','1,284 records','326 orders','8,421 documents','14 locations'][i]}</p><button className="mt-5 text-[11px] font-bold">Open workspace →</button></div>)}</div></Section>}

function ProjectWorkspace(){return <Section eyebrow="Projects" title="Project portfolio"><div className="grid gap-4 xl:grid-cols-2">{projects.map(p=><div key={p[0]} className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-start justify-between gap-4"><div><div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{p[1]}</div><h3 className="mt-1 font-bold">{p[0]}</h3></div><span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${p[4]==='Attention'?'bg-amber-50 text-amber-700':'bg-emerald-50 text-emerald-700'}`}>{p[4]}</span></div><div className="mt-6 flex justify-between text-xs"><span className="text-slate-500">Progress <b className="text-slate-900">{p[2]}</b></span><b>{p[3]}</b></div><div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className="h-full rounded-full bg-slate-900" style={{width:p[2]}}/></div><div className="mt-5 grid grid-cols-3 gap-3 text-[11px]"><div><span className="text-slate-400">Contract</span><b className="mt-1 block">Active</b></div><div><span className="text-slate-400">Procurement</span><b className="mt-1 block">8 packages</b></div><div><span className="text-slate-400">Risk</span><b className="mt-1 block">Low</b></div></div></div>)}</div></Section>}

function ContractsWorkspace(){return <DataTable title="Contract portfolio" subtitle="Obligations, exposure, claims and critical dates" cols={['Contract','Counterparty','Value','Status','Expiry']} rows={[['CNT-2026-041','Atlas Engineering','$4.8M','Active','30 Sep 2026'],['CNT-2026-038','Delta Materials','$2.1M','Review','12 Oct 2026'],['CNT-2026-032','Nile Electromech','$6.4M','Active','18 Dec 2026'],['CNT-2026-019','Cairo Steel','$1.7M','Claim','02 Nov 2026']]}/>}
function ProcurementWorkspace(){return <DataTable title="Procurement control tower" subtitle="From request to purchase order" cols={['Request','Package','Value','Stage','Supplier']} rows={[['PR-1042','Structural steel','$1.24M','Awarded','Atlas Engineering'],['PR-1038','HVAC package','$780K','Evaluation','Nile Electromech'],['PR-1031','Electrical materials','$412K','PO Issued','Delta Materials'],['PR-1027','Finishing package','$286K','Approval','Cairo Steel']]}/>}
function FinanceWorkspace(){return <div className="space-y-5"><div className="grid gap-4 md:grid-cols-3">{[['Revenue YTD','$42.8M'],['Gross Margin','23.6%'],['Receivables','$7.3M']].map(x=><div key={x[0]} className="rounded-2xl border border-slate-200 bg-white p-6"><div className="text-xs text-slate-500">{x[0]}</div><div className="mt-2 text-3xl font-bold tracking-tight">{x[1]}</div></div>)}</div><div className="rounded-2xl border border-slate-200 bg-white p-6"><h3 className="font-bold">Cash flow forecast</h3><div className="mt-8 flex h-56 items-end gap-2">{[42,48,55,51,63,70,62,76,81,78,91,96].map((h,i)=><div key={i} className="flex-1 rounded-t bg-slate-900/90" style={{height:`${h}%`}}/>)}</div></div></div>}
function AIWorkspace({prompt,setPrompt,answer,ask}:{prompt:string;setPrompt:(s:string)=>void;answer:string;ask:()=>void}){return <div className="grid gap-5 xl:grid-cols-[1fr_330px]"><div className="rounded-2xl border border-slate-200 bg-white"><div className="border-b p-6"><div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Intelligence</div><h2 className="mt-1 text-xl font-bold">AI Workforce</h2><p className="mt-1 text-xs text-slate-500">AI operates across the connected business context.</p></div><div className="min-h-64 p-6"><div className="max-w-3xl rounded-2xl bg-slate-950 p-5 text-sm leading-6 text-slate-200">{answer}</div></div><div className="border-t p-4"><div className="flex gap-2"><input value={prompt} onChange={e=>setPrompt(e.target.value)} className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-slate-400" /><button onClick={ask} className="rounded-xl bg-slate-950 px-5 text-xs font-bold text-white">Ask EOS</button></div></div></div><div className="rounded-2xl border border-slate-200 bg-white p-6"><h3 className="font-bold">Digital workers</h3>{['Executive Analyst','Commercial Agent','Procurement Agent','Finance Agent','Project Agent'].map(x=><div key={x} className="mt-3 flex items-center justify-between rounded-xl bg-slate-50 p-3"><span className="text-xs font-semibold">{x}</span><span className="text-[10px] font-bold text-emerald-600">ACTIVE</span></div>)}</div></div>}
function AutomationWorkspace({onAction}:{onAction:(m:string)=>void}){return <Section eyebrow="Automation" title="Automation Center"><div className="space-y-3">{[['Invoice approval','Finance → Manager → ERP','98%'],['Purchase order control','Procurement → Budget → Supplier','94%'],['Contract expiry','Legal → Commercial → Executive','100%'],['Project risk escalation','Project → AI → Executive','81%']].map(x=><div key={x[0]} className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 md:flex-row md:items-center md:justify-between"><div><b className="text-sm">{x[0]}</b><div className="mt-1 text-xs text-slate-500">{x[1]}</div></div><div className="flex items-center gap-5"><span className="text-xs font-bold">{x[2]}</span><span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-bold text-emerald-700">ACTIVE</span><button onClick={()=>onAction(`Opened workflow: ${x[0]}`)} className="text-xs font-bold">Open →</button></div></div>)}</div></Section>}
function AnalyticsWorkspace(){return <Section eyebrow="Intelligence" title="Business analytics"><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{[['Executive','Business health'],['Financial','Cash & profitability'],['Projects','Delivery & cost'],['Procurement','Spend & suppliers']].map(x=><div key={x[0]} className="rounded-2xl border border-slate-200 bg-white p-5"><div className="text-xs text-slate-500">{x[0]}</div><div className="mt-2 text-lg font-bold">{x[1]}</div><div className="mt-5 h-16 flex items-end gap-1">{[30,48,38,62,54,72,66,82].map((h,i)=><div key={i} className="flex-1 rounded-t bg-slate-900/80" style={{height:`${h}%`}}/>)}</div></div>)}</div></Section>}
function GraphWorkspace(){return <Section eyebrow="Connected intelligence" title="Business Graph"><div className="relative h-[500px] overflow-hidden rounded-2xl border border-slate-800 bg-[#080d18]"><div className="absolute inset-0 opacity-25" style={{backgroundImage:'radial-gradient(circle,#64748b 1px,transparent 1px)',backgroundSize:'32px 32px'}}/>{[['50%','48%','North Coast Hub',true],['20%','25%','Contract CNT-041',false],['80%','25%','Steel Package',false],['18%','72%','Atlas Engineering',false],['82%','72%','Invoice INV-882',false],['50%','84%','Purchase Order PO-1042',false]].map((n,i)=><div key={n[2]} style={{left:n[0],top:n[1],transform:'translate(-50%,-50%)'}} className={`absolute rounded-xl border px-4 py-3 text-center shadow-xl ${n[3]?'border-white bg-white text-slate-950':'border-white/10 bg-slate-900 text-slate-200'}`}><b className="text-xs">{n[2]}</b><div className="mt-1 text-[9px] opacity-60">{n[3]?'Project':'Connected object'}</div></div>)}</div></Section>}
function DocumentsWorkspace(){return <DataTable title="Document workspace" subtitle="Documents connected to business context" cols={['Document','Type','Related to','Version','Updated']} rows={[['Main Contract CNT-041','Contract','North Coast Hub','v7','Today'],['Steel Technical Submittal','Technical','PR-1042','v3','Yesterday'],['Invoice INV-882','Financial','PO-1042','v2','Sep 23'],['Project Risk Register','Risk','North Coast Hub','v12','Sep 22']]}/>}
function DataTable({title,subtitle,cols,rows}:{title:string;subtitle:string;cols:string[];rows:string[][]}){return <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white"><div className="border-b border-slate-100 p-6"><h2 className="font-bold">{title}</h2><p className="mt-1 text-xs text-slate-500">{subtitle}</p></div><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-400"><tr>{cols.map(c=><th key={c} className="px-5 py-3 font-bold">{c}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i} className="border-t border-slate-100 hover:bg-slate-50">{r.map((v,j)=><td key={j} className={`px-5 py-4 ${j===0?'font-semibold text-slate-800':'text-slate-500'}`}>{v}</td>)}</tr>)}</tbody></table></div></div>}
function OwnerOverview(){return <div className="space-y-8"><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[['Organizations','48','+6 this month'],['Active Users','2,841','98.2% active'],['AI Usage','18.4K','tasks this month'],['Platform Health','99.98%','All core services']].map(x=><div key={x[0]} className="rounded-2xl border border-slate-200 bg-white p-5"><div className="text-xs text-slate-500">{x[0]}</div><div className="mt-2 text-2xl font-bold">{x[1]}</div><div className="mt-2 text-[11px] font-semibold text-emerald-600">{x[2]}</div></div>)}</div><Section eyebrow="Platform" title="Control plane"><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{['Tenant lifecycle','Subscriptions & billing','AI governance','Security & audit','System health','Platform usage'].map(x=><div key={x} className="rounded-2xl border border-slate-200 bg-white p-5"><h3 className="font-bold">{x}</h3><p className="mt-2 text-xs leading-5 text-slate-500">Manage and monitor this platform capability from the control plane.</p><div className="mt-5 text-[11px] font-bold">Open →</div></div>)}</div></Section></div>}
function OwnerTable({title,subtitle,rows}:{title:string;subtitle:string;rows:string[][]}){return <DataTable title={title} subtitle={subtitle} cols={['Resource','Context','Status','Detail']} rows={rows}/>}

