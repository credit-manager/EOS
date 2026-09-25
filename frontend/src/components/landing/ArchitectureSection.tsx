import { useI18n } from '../../i18n';
import Reveal from './Reveal';

const EOS_LAYERS = ['archEosFlow1', 'archEosFlow2', 'archEosFlow3', 'archEosFlow4', 'archEosFlow5', 'archEosFlow6'] as const;

const TONE_BY_INDEX = [
  'bg-blue-500/15 border-blue-500/30 text-blue-300',
  'bg-blue-500/20 border-blue-400/40 text-blue-200',
  'bg-blue-500/25 border-blue-400/50 text-blue-100',
  'bg-blue-500/35 border-blue-400/60 text-white',
  'bg-blue-500/50 border-blue-400/70 text-white',
  'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-600/30',
];

function CheckIcon() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0l-3.5-3.5a1 1 0 1 1 1.4-1.4l2.8 2.8 6.8-6.8a1 1 0 0 1 1.4 0Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M6.3 6.3a1 1 0 0 1 1.4 0L10 8.6l2.3-2.3a1 1 0 1 1 1.4 1.4L11.4 10l2.3 2.3a1 1 0 0 1-1.4 1.4L10 11.4l-2.3 2.3a1 1 0 0 1-1.4-1.4L8.6 10 6.3 7.7a1 1 0 0 1 0-1.4Z" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg
      className="h-4 w-4 shrink-0 text-slate-600 rtl:rotate-180"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M10.3 5.3a1 1 0 0 1 1.4 0l5 5a1 1 0 0 1 0 1.4l-5 5a1 1 0 0 1-1.4-1.4L14 11H4a1 1 0 0 1 0-2h10l-3.7-3.7a1 1 0 0 1 0-1.4Z" />
    </svg>
  );
}

export default function ArchitectureSection() {
  const { t } = useI18n();

  const problems = [
    t.landing.archTraditionalProblem1,
    t.landing.archTraditionalProblem2,
    t.landing.archTraditionalProblem3,
  ];

  return (
    <section id="architecture" className="relative scroll-mt-20 overflow-hidden bg-slate-950 py-24 md:py-32">
      <div className="absolute inset-0 hero-grid" aria-hidden="true" />
      <div
        className="absolute left-1/2 top-0 h-px w-4/5 -translate-x-1/2 bg-gradient-to-r from-transparent via-blue-600/50 to-transparent"
        aria-hidden="true"
      />

      <div className="relative mx-auto max-w-7xl px-6">
        <Reveal className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-500">
            {t.landing.archTitle}
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
            {t.landing.archSubtitle}
          </h2>
        </Reveal>

        <div className="mt-14 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Traditional ERP */}
          <Reveal delay={80}>
            <div className="flex h-full flex-col rounded-2xl border border-white/8 bg-white/[0.02] p-7 md:p-8">
              <div className="flex items-center gap-3">
                <span className="h-2.5 w-2.5 rounded-full bg-slate-600" />
                <h3 className="text-xl font-semibold text-slate-300">{t.landing.archTraditional}</h3>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-slate-500">{t.landing.archTraditionalDesc}</p>

              <div className="mt-7 flex flex-col items-stretch gap-3">
                {[t.landing.archTraditionalFlow1, t.landing.archTraditionalFlow2, t.landing.archTraditionalFlow3].map(
                  (stage, index) => (
                    <div key={stage} className="flex items-center gap-3">
                      <div className="flex-1 rounded-lg border border-white/8 bg-white/[0.03] px-4 py-3 text-center text-sm font-medium text-slate-400">
                        {stage}
                      </div>
                      {index < 2 && (
                        <div className="flex justify-center lg:hidden">
                          <ArrowIcon />
                        </div>
                      )}
                    </div>
                  )
                )}
                <div className="mt-1 hidden justify-center lg:flex lg:rotate-90">
                  <ArrowIcon />
                </div>
              </div>

              <ul className="mt-7 space-y-3 border-t border-white/6 pt-6">
                {problems.map((problem) => (
                  <li key={problem} className="flex items-start gap-3 text-sm text-slate-400">
                    <span className="mt-0.5 text-red-400/80">
                      <XIcon />
                    </span>
                    {problem}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          {/* 2TO EOS */}
          <Reveal delay={160}>
            <div className="flex h-full flex-col rounded-2xl border border-blue-500/30 bg-gradient-to-b from-blue-600/10 to-transparent p-7 md:p-8">
              <div className="flex items-center gap-3">
                <span className="h-2.5 w-2.5 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]" />
                <h3 className="text-xl font-semibold text-white">{t.landing.archEos}</h3>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-slate-400">{t.landing.archEosDesc}</p>

              <div className="mt-7 flex flex-1 flex-col gap-2">
                {EOS_LAYERS.map((key, index) => (
                  <div
                    key={key}
                    className={`flex items-center justify-between rounded-lg border px-4 py-3 text-sm font-medium transition-transform duration-500 hover:translate-x-1 ${TONE_BY_INDEX[index]}`}
                  >
                    <span>{t.landing[key]}</span>
                    <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider opacity-70">
                      {index === 0 ? '—' : <ArrowIcon />}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-7 flex items-start gap-3 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                <span className="mt-0.5">
                  <CheckIcon />
                </span>
                {t.landing.archErosionNote}
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
