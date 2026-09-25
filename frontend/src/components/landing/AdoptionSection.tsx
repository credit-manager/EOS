import { useI18n } from '../../i18n';
import Reveal from './Reveal';

function CheckIcon() {
  return (
    <svg className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0l-3.5-3.5a1 1 0 1 1 1.4-1.4l2.8 2.8 6.8-6.8a1 1 0 0 1 1.4 0Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

type Plan = {
  name: string;
  description: string;
  price: string;
  period: string;
  features: string[];
  popular: boolean;
};

export default function AdoptionSection({ onShowLogin }: { onShowLogin: () => void }) {
  const { t } = useI18n();

  const plans: Plan[] = [
    {
      name: t.landing.adoptPlatform,
      description: t.landing.adoptPlatformDesc,
      price: t.landing.adoptPriceStarter,
      period: t.landing.adoptPricePeriod,
      features: [
        t.landing.adoptStarterFeature1,
        t.landing.adoptStarterFeature2,
        t.landing.adoptStarterFeature3,
        t.landing.adoptStarterFeature4,
      ],
      popular: false,
    },
    {
      name: t.landing.adoptBusiness,
      description: t.landing.adoptBusinessDesc,
      price: t.landing.adoptPricePro,
      period: t.landing.adoptPricePeriod,
      features: [
        t.landing.adoptProFeature1,
        t.landing.adoptProFeature2,
        t.landing.adoptProFeature3,
        t.landing.adoptProFeature4,
      ],
      popular: true,
    },
    {
      name: t.landing.adoptEnterprise,
      description: t.landing.adoptEnterpriseDesc,
      price: t.landing.adoptPriceEnt,
      period: t.landing.adoptPricePeriod,
      features: [
        t.landing.adoptEntFeature1,
        t.landing.adoptEntFeature2,
        t.landing.adoptEntFeature3,
        t.landing.adoptEntFeature4,
      ],
      popular: false,
    },
  ];

  return (
    <section id="adoption" className="scroll-mt-20 border-t border-slate-200 bg-slate-50 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <Reveal className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">
            {t.landing.adoptTitle}
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-slate-900 md:text-5xl">
            {t.landing.adoptSubtitle}
          </h2>
        </Reveal>

        <div className="mx-auto mt-14 grid max-w-6xl grid-cols-1 items-stretch gap-6 lg:grid-cols-3">
          {plans.map((plan, index) => (
            <Reveal key={plan.name} delay={index * 90}>
              <div
                className={`flex h-full flex-col rounded-2xl bg-white p-7 transition-all duration-300 md:p-8 ${
                  plan.popular
                    ? 'border-2 border-blue-600 shadow-xl shadow-blue-600/10 lg:-my-3'
                    : 'border border-slate-200 shadow-sm hover:shadow-md'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-lg font-semibold text-slate-900">{plan.name}</h3>
                  {plan.popular && (
                    <span className="rounded-full bg-blue-600 px-3 py-1 text-[11px] font-semibold text-white">
                      {t.landing.adoptPopular}
                    </span>
                  )}
                </div>

                <p className="mt-2 text-sm leading-relaxed text-slate-500">{plan.description}</p>

                <div className="mt-6 flex items-end gap-2">
                  <span className="text-5xl font-bold tracking-tight tabular-nums text-slate-900">
                    {plan.price}
                  </span>
                  <span className="mb-2 text-sm text-slate-500">{plan.period}</span>
                </div>

                <div className="mt-6 border-t border-slate-100 pt-5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  {t.landing.adoptIncludes}
                </div>

                <ul className="mt-4 flex-1 space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm text-slate-600">
                      <span className="text-blue-600">
                        <CheckIcon />
                      </span>
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={onShowLogin}
                  className={`mt-7 w-full rounded-xl py-3 text-sm font-semibold transition-colors ${
                    plan.popular
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'border border-slate-300 bg-white text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  {plan.popular ? t.landing.adoptCta : t.landing.adoptContact}
                </button>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={120}>
          <p className="mx-auto mt-8 max-w-2xl text-center text-xs leading-relaxed text-slate-400">
            {t.landing.adoptNote}
          </p>
        </Reveal>
      </div>
    </section>
  );
}
