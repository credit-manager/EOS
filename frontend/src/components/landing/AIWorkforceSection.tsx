import { useI18n } from '../../i18n';
import Reveal from './Reveal';

type IconProps = { className?: string };

function FinanceIcon({ className = 'h-5 w-5' }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M3 20h18M7 20V10m5 10V5m5 15v-7" strokeLinecap="round" />
    </svg>
  );
}

function OperationsIcon({ className = 'h-5 w-5' }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </svg>
  );
}

function SalesIcon({ className = 'h-5 w-5' }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="m3 17 6-6 4 4 8-8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 7h7v7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ProcurementIcon({ className = 'h-5 w-5' }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M3 7h2l2.4 10.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 10H6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="10" cy="21" r="1.2" />
      <circle cx="17" cy="21" r="1.2" />
    </svg>
  );
}

function ExecutiveIcon({ className = 'h-5 w-5' }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18" strokeLinecap="round" />
    </svg>
  );
}

const AGENT_ICONS = [FinanceIcon, OperationsIcon, SalesIcon, ProcurementIcon, ExecutiveIcon];

export default function AIWorkforceSection() {
  const { t } = useI18n();

  const agents = [
    { title: t.landing.aiFinance, desc: t.landing.aiFinanceDesc },
    { title: t.landing.aiOperations, desc: t.landing.aiOperationsDesc },
    { title: t.landing.aiSales, desc: t.landing.aiSalesDesc },
    { title: t.landing.aiProcurement, desc: t.landing.aiProcurementDesc },
    { title: t.landing.aiExecutive, desc: t.landing.aiExecutiveDesc },
  ];

  const capabilities = [
    t.landing.aiCapContext,
    t.landing.aiCapPlanning,
    t.landing.aiCapTools,
    t.landing.aiCapPolicy,
    t.landing.aiCapVerify,
    t.landing.aiCapAudit,
  ];

  return (
    <section id="ai" className="scroll-mt-20 bg-white py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:items-end">
          <Reveal className="lg:col-span-7">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">
              {t.landing.navAiWorkforce}
            </p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-slate-900 md:text-5xl">
              {t.landing.aiTitle}
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-slate-500">{t.landing.aiSubtitle}</p>
          </Reveal>
          <Reveal delay={100} className="lg:col-span-5">
            <p className="border-s-4 border-blue-600 ps-5 text-sm leading-relaxed text-slate-600">
              {t.landing.aiNotChatbot}
            </p>
          </Reveal>
        </div>

        <Reveal delay={60} className="mt-8">
          <p className="max-w-3xl text-sm leading-relaxed text-slate-500">{t.landing.aiIntro}</p>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent, index) => {
            const Icon = AGENT_ICONS[index];
            return (
              <Reveal key={agent.title} delay={index * 70}>
                <div className="group flex h-full flex-col rounded-xl border border-slate-200 bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-blue-300 hover:shadow-lg hover:shadow-blue-100/70">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm shadow-blue-600/30 transition-transform duration-300 group-hover:scale-110">
                    <Icon />
                  </div>
                  <h3 className="mt-5 text-base font-semibold text-slate-900">{agent.title}</h3>
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-500">{agent.desc}</p>
                </div>
              </Reveal>
            );
          })}

          <Reveal delay={350}>
            <div className="flex h-full flex-col justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6">
              <div className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                {t.landing.aiCapabilities}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {capabilities.map((capability) => (
                  <span
                    key={capability}
                    className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600"
                  >
                    {capability}
                  </span>
                ))}
              </div>
            </div>
          </Reveal>
        </div>

        <Reveal delay={80}>
          <div className="mt-10 flex items-start gap-4 rounded-xl border border-slate-200 bg-slate-50 p-6">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white">
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path
                  fillRule="evenodd"
                  d="M10 1.5a4 4 0 0 0-4 4v2.5H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2h-1V5.5a4 4 0 0 0-4-4Zm2.5 6.5h-5V5.5a2.5 2.5 0 1 1 5 0v2.5Z"
                  clipRule="evenodd"
                />
              </svg>
            </span>
            <p className="text-sm leading-relaxed text-slate-600">{t.landing.aiGovernedNote}</p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
