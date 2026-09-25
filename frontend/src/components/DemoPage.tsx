import { useState } from 'react';

const items = [
  ['overview','Executive Dashboard','⌂'],
  ['projects','Projects','▦'],
  ['contracts','Contracts','□'],
  ['procurement','Procurement','⇄'],
  ['financial','Financial','$'],
  ['ai','AI Workforce','✦'],
  ['graph','Business Graph','◎'],
  ['workflows','Automation','⚡'],
] as const;

const projects = [
  ['North Coast Logistics Hub','Construction','78%','$18.4M','On Track'],
  ['Cairo Industrial Expansion','Industrial','61%','$11.7M','Attention'],
  ['Delta Water Infrastructure','Infrastructure','92%','$24.1M','On Track'],
  ['New Capital Operations Center','Facilities','44%','$8.9M','On Track'],
];

export default function DemoPage({onExit}:{onExit:()=>void}) {
  const [page,setPage]=useState('overview');
  const [message,setMessage]=useState('');
  const [prompt,setPrompt]=useState('What requires executive attention today?');
  const [answer,setAnswer]=useState('Three items require attention: one contract approval, a procurement variance on the steel package, and three receivables approaching due date.');
  const notify=(m:string)=>{setMessage(m);setTimeout(()=>setMessage(''),2200)};
  return <div className="min-h-screen bg-[#f6f8fc] text-slate-900">
    <header className="sticky top-0 z-50 flex h-14 items-center justify-between bg-slate-950 px-5 text-white shadow-xl">
      <div className="flex items-center gap-3"><b className="rounded-lg bg-indigo-600 px-2 py-1 text-xs">2TO</b><div><b>2TO EOS</b><div className="text-[9px] uppercase tracking-widest text-slate-400">Interactive Product Demo</div></div></div>
      <div className="flex items-center gap-3"><span className="rounded-full bg-emerald-500/10 px-3 py-1 text-[10px] font-bold text-emerald-300">DEMO ENVIRONMENT</span><button onClick={onExit} className="rounded-lg border border-white/15 px-3 py-1.5 text-xs">Exit</button></div>
    </header>
    <div className="flex min-h-[calc(100vh-56px)]">
      <aside className="hidden w-64 border-r border-slate-200 bg-white p-4 lg:block">
        <div className="mb-5 px-3 text-[10px] font-bold uppercase tracking-widest text-slate-400">Business OS</div>
        {items.map(([id,label,icon])=><button key={id} onClick={()=>setPage(id)} className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium ${page===id?'bg-indigo-50 text-indigo-700':'text-slate-600 hover:bg-slate-50'}`}><span className="w-6 text-center">{icon}</span>{label}</button>)}
        <div className="mt-7 rounded-2xl border border-indigo-100 bg-indigo-50 p-4"><b className="text-xs">Demo tenant</b><div className="mt-1 font-bold">Nile Horizon Group</div><p className="mt-2 text-[10px] leading-5 text-slate-500">Sample enterprise data. No real customer records are connected.</p></div>
      </aside>
      <main className="min-w-0 flex-1">
        <div className="border-b bg-white px-5 py-4 lg:px-8"><div className="mx-auto flex max-w-[1500px] items-center justify-between"><div><div className="text-[11px] text-slate-400">Nile Horizon Group / Business OS</div><h1 className="mt-1 text-xl font-bold">{items.find(x=>x[0]===page)?.[1]}</h1></div><button onClick={()=>notify('Demo action completed — no live data was changed.')} className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white">Create</button></div></div>
        <div className="mx-auto max-w-[1500px] p-4 lg:p-8">{message&&<div className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{message}</div>}
          {page==='overview'&&<Overview onAction={notify}/>}
          {page==='projects'&&<Table title="Project portfolio" cols={['Project','Type','Progress','Budget','Status']} rows={projects}/>}
          {page==='contracts'&&<Table title="Contract register" cols={['Contract','Counterparty','Value','Status','Due']} rows={[['CNT-2026-041','Atlas Engineering','$4.8M','In Progress','Sep 30'],['CNT-2026-038','Delta Materials','$2.1M','Review','Oct 12'],['CNT-2026-032','Nile Electromech','$6.4M','Active','Dec 18']]}/>}
          {page==='procurement'&&<Table title="Procurement control tower" cols={['Request','Package','Value','Stage','Supplier']} rows={[['PR-1042','Structural steel','$1.24M','Awarded','Atlas Engineering'],['PR-1038','HVAC package','$780K','Evaluation','Nile Electromech'],['PR-1031','Electrical materials','$412K','PO Issued','Delta Materials']]}/>}
          {page==='financial'&&<Financial/>}
          {page==='ai'&&<AI prompt={prompt} setPrompt={setPrompt} answer={answer} ask={()=>{setAnswer('EOS analyzed projects, contracts, procurement and finance and identified the highest-impact executive actions.');notify('AI analysis completed.')}}/>}
          {page==='graph'&&<Graph/>}
          {page==='workflows'&&<Workflows onAction={notify}/>}
        </div>
      </main>
    </div>
  </div>;
}

function Overview({onAction}:{onAction:(m:string)=>void}) {
 const cards=[['Portfolio Value','$63.1M','+8.4%'],['Active Projects','24','+3'],['Contract Exposure','$31.7M','6.2% at risk'],['Cash Position','$12.8M','+14.1%']];
 return <><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(c=><div className="rounded-2xl border bg-white p-5 shadow-sm" key={c[0]}><div className="text-xs text-slate-500">{c[0]}</div><div className="mt-2 flex justify-between text-2xl font-bold"><span>{c[1]}</span><span className="text-xs text-emerald-600">{c[2]}</span></div><div className="mt-1 text-[11px] text-slate-400">vs previous period</div></div>)}</div>
 <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]"><div className="rounded-2xl border bg-white p-6 shadow-sm"><h2 className="font-bold">Portfolio performance</h2><p className="text-xs text-slate-500">Revenue, committed cost and forecast</p><div className="mt-8 flex h-52 items-end gap-2">{[42,55,48,64,58,72,69,84,77,92,86,100].map((h,i)=><div key={i} className="flex-1 rounded-t bg-indigo-500" style={{height:h+'%'}}/>)}</div></div>
 <div className="rounded-2xl border bg-white p-6 shadow-sm"><h2 className="font-bold">Executive signals</h2><p className="text-xs text-slate-500">AI-prioritized actions</p><div className="mt-5 space-y-3">{[['Cash collection','3 invoices due within 7 days.'],['Procurement','Steel package is 6% above benchmark.'],['Contract','CNT-2026-038 requires approval.'],['Project','North Coast is ahead of plan.']].map(x=><button onClick={()=>onAction('Opened signal: '+x[0])} key={x[0]} className="w-full rounded-xl bg-slate-50 p-3 text-left hover:bg-indigo-50"><b className="text-xs">{x[0]}</b><div className="mt-1 text-xs text-slate-500">{x[1]}</div></button>)}</div></div></div>
 <div className="mt-6 grid gap-3 md:grid-cols-4">{[['Projects','24','3 need attention'],['Contracts','118','7 pending action'],['Procurement','$9.6M','31 commitments'],['Automation','87%','18 workflows active']].map(x=><div className="rounded-xl border bg-white p-4" key={x[0]}><div className="text-xs text-slate-500">{x[0]}</div><b className="text-xl">{x[1]}</b><div className="text-[11px] text-slate-400">{x[2]}</div></div>)}</div></>;
}

function Table({title,cols,rows}:{title:string;cols:string[];rows:string[][]}){return <div className="overflow-hidden rounded-2xl border bg-white shadow-sm"><div className="border-b p-6"><h2 className="font-bold">{title}</h2><p className="text-xs text-slate-500">Connected operational records</p></div><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-[10px] uppercase text-slate-400"><tr>{cols.map(c=><th className="px-5 py-3" key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr className="border-t hover:bg-slate-50" key={i}>{r.map((v,j)=><td className={`px-5 py-4 ${j===0?'font-semibold text-slate-800':'text-slate-500'}`} key={j}>{v}</td>)}</tr>)}</tbody></table></div></div>}

function Financial(){return <div className="space-y-6"><div className="grid gap-4 md:grid-cols-3">{[['Revenue YTD','$42.8M'],['Gross Margin','23.6%'],['Receivables','$7.3M']].map(x=><div className="rounded-2xl border bg-white p-6 shadow-sm" key={x[0]}><div className="text-xs text-slate-500">{x[0]}</div><b className="mt-2 block text-3xl">{x[1]}</b></div>)}</div><div className="rounded-2xl border bg-white p-6 shadow-sm"><h2 className="font-bold">Cash flow forecast</h2><div className="mt-8 flex h-56 items-end gap-2">{[45,50,58,54,66,72,61,76,82,78,91,96].map((h,i)=><div className="flex-1 rounded-t bg-indigo-500/80" style={{height:h+'%'}} key={i}/>)}</div></div></div>}

function AI({prompt,setPrompt,answer,ask}:{prompt:string;setPrompt:(s:string)=>void;answer:string;ask:()=>void}){return <div className="grid gap-6 xl:grid-cols-[1fr_340px]"><div className="rounded-2xl border bg-white shadow-sm"><div className="border-b p-6"><div className="flex items-center gap-3"><span className="rounded-xl bg-indigo-600 p-3 text-white">✦</span><div><b>EOS AI Workforce</b><p className="text-xs text-slate-500">Business-aware assistant</p></div></div></div><div className="min-h-56 p-6"><div className="rounded-2xl bg-slate-100 p-4 text-sm leading-6">{answer}</div></div><div className="border-t p-4 flex gap-2"><input value={prompt} onChange={e=>setPrompt(e.target.value)} className="flex-1 rounded-xl border bg-slate-50 px-4 py-3 text-sm" /><button onClick={ask} className="rounded-xl bg-indigo-600 px-5 text-sm font-bold text-white">Ask EOS</button></div></div><div className="rounded-2xl border bg-white p-6 shadow-sm"><b>AI workforce</b>{['Executive Analyst','Commercial Agent','Procurement Agent','Finance Agent'].map(x=><div className="mt-3 flex justify-between rounded-xl bg-slate-50 p-3 text-sm" key={x}>{x}<span className="text-emerald-500">●</span></div>)}</div></div>}

function Graph(){return <div className="rounded-2xl border bg-white p-6 shadow-sm"><h2 className="font-bold">Business Graph</h2><p className="text-xs text-slate-500">One connected model across operational entities</p><div className="relative mt-6 h-[430px] overflow-hidden rounded-2xl bg-slate-950"><div className="absolute inset-0 opacity-30" style={{backgroundImage:'radial-gradient(circle,#6366f1 1px,transparent 1px)',backgroundSize:'32px 32px'}}/>{[['50%','46%','North Coast Hub'],['20%','25%','Contract CNT-041'],['80%','25%','Steel Package'],['20%','72%','Atlas Engineering'],['80%','72%','Invoice INV-882']].map((n,i)=><div key={n[2]} style={{left:n[0],top:n[1],transform:'translate(-50%,-50%)'}} className={`absolute rounded-xl border px-4 py-3 text-center ${i===0?'border-indigo-300 bg-indigo-600 text-white':'border-white/10 bg-slate-900 text-slate-200'}`}><b className="text-xs">{n[2]}</b><div className="text-[9px] opacity-60">{i===0?'Project':'Business Object'}</div></div>)}</div></div>}

function Workflows({onAction}:{onAction:(m:string)=>void}){return <div className="rounded-2xl border bg-white shadow-sm"><div className="border-b p-6"><h2 className="font-bold">Automation control center</h2><p className="text-xs text-slate-500">Business rules turned into executable workflows</p></div>{[['Invoice approval','Finance → Manager → ERP','98%'],['Purchase order control','Procurement → Budget → Supplier','94%'],['Contract expiry','Legal → Commercial → Executive','100%'],['Project risk escalation','Project → AI → Executive','81%']].map(x=><div className="flex items-center justify-between border-b p-5" key={x[0]}><div><b className="text-sm">{x[0]}</b><div className="text-xs text-slate-500">{x[1]}</div></div><div className="flex items-center gap-5"><span className="text-xs font-bold text-slate-500">{x[2]}</span><span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-bold text-emerald-700">ACTIVE</span><button onClick={()=>onAction('Opened workflow: '+x[0])} className="text-xs font-bold text-indigo-600">Open →</button></div></div>)}</div>}
