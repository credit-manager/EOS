import LanguageSwitcher from './LanguageSwitcher';
import { useI18n } from '../i18n';

const BRANDS = [
  'Nexora',
  'Veltrix',
  'Orbital',
  'Lumina',
  'Quantum',
  'Aether',
  'Northwind',
  'Zenith',
];

export default function LandingPage({ onShowLogin }: { onShowLogin: () => void }) {
  const { language, setLanguage, isRTL, t } = useI18n();

  const openDemo = () => { window.location.href = `${window.location.pathname}?demo=1`; };

  const navLinks = [
    { label: t.landing.features, href: '#features' },
    { label: t.landing.solutions, href: '#solutions' },
    { label: t.landing.pricing, href: '#pricing' },
    { label: t.landing.footerLinkSecurity, href: '#security' },
  ];

  const features = [
    { icon: '🔗', title: t.landing.featureConnectTitle, desc: t.landing.featureConnectDesc },
    { icon: '🧠', title: t.landing.featureUnderstandTitle, desc: t.landing.featureUnderstandDesc },
    {
      icon: '⚙️',
      title: t.landing.featureOrchestrateTitle,
      desc: t.landing.featureOrchestrateDesc,
    },
    { icon: '🚀', title: t.landing.featureExecuteTitle, desc: t.landing.featureExecuteDesc },
    { icon: '📊', title: t.landing.featureAnalyzeTitle, desc: t.landing.featureAnalyzeDesc },
    { icon: '🛡️', title: t.landing.featureGovernTitle, desc: t.landing.featureGovernDesc },
  ];

  const steps = [
    { number: '1', title: t.landing.step1Title, desc: t.landing.step1Desc },
    { number: '2', title: t.landing.step2Title, desc: t.landing.step2Desc },
    { number: '3', title: t.landing.step3Title, desc: t.landing.step3Desc },
    { number: '4', title: t.landing.step4Title, desc: t.landing.step4Desc },
  ];

  const stats = [
    { value: '99.9%', label: t.landing.statUptime },
    { value: '<100ms', label: t.landing.statResponse },
    { value: '500+', label: t.landing.statIntegrations },
    { value: '10K+', label: t.landing.statBusinesses },
  ];

  const plans = [
    {
      name: t.landing.starterPlan,
      price: '$29',
      period: t.landing.perMonth,
      features: [
        t.landing.starterFeature1,
        t.landing.starterFeature2,
        t.landing.starterFeature3,
        t.landing.starterFeature4,
      ],
      cta: t.landing.startTrial,
      popular: false,
    },
    {
      name: t.landing.professionalPlan,
      price: '$99',
      period: t.landing.perMonth,
      features: [
        t.landing.proFeature1,
        t.landing.proFeature2,
        t.landing.proFeature3,
        t.landing.proFeature4,
      ],
      cta: t.landing.startTrial,
      popular: true,
    },
    {
      name: t.landing.enterprisePlan,
      price: t.landing.contactSales,
      period: '',
      features: [
        t.landing.entFeature1,
        t.landing.entFeature2,
        t.landing.entFeature3,
        t.landing.entFeature4,
      ],
      cta: t.landing.getStarted,
      popular: false,
    },
  ];

  const footerColumns = [
    {
      title: t.landing.footerProduct,
      links: [
        { label: t.landing.footerLinkPlatform, href: '#features' },
        { label: t.landing.footerLinkFeatures, href: '#features' },
        { label: t.landing.footerLinkPricing, href: '#pricing' },
        { label: t.landing.footerLinkSecurity, href: '#security' },
      ],
    },
    {
      title: t.landing.footerCompany,
      links: [
        { label: t.landing.footerLinkAbout, href: '#' },
        { label: t.landing.footerLinkBlog, href: '#' },
        { label: t.landing.footerLinkCareers, href: '#' },
        { label: t.landing.footerLinkContact, href: '#' },
      ],
    },
    {
      title: t.landing.footerResources,
      links: [
        { label: t.landing.footerLinkDocs, href: '#' },
        { label: t.landing.footerLinkApi, href: '#' },
        { label: t.landing.footerLinkStatus, href: '#' },
        { label: t.landing.footerLinkSupport, href: '#' },
      ],
    },
    {
      title: t.landing.footerLegal,
      links: [
        { label: t.landing.footerLinkPrivacy, href: '#' },
        { label: t.landing.footerLinkTerms, href: '#' },
        { label: t.landing.footerLinkCookies, href: '#' },
        { label: t.landing.footerLinkCompliance, href: '#' },
      ],
    },
  ];

  const trustIndicators = [t.landing.soc2, t.landing.gdpr, t.landing.uptime];

  return (
    <div className={`min-h-screen bg-white ${isRTL ? 'rtl' : 'ltr'}`}>
      {/* Sticky Navigation */}
      <nav className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <a href="#" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg shadow-indigo-600/30">
              <span className="text-sm font-bold text-white">2TO</span>
            </div>
            <span className="text-lg font-bold tracking-tight text-white">EOS</span>
          </a>

          <div className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <a
                key={link.href + link.label}
                href={link.href}
                className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-white p-0.5">
              <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={isRTL} />
            </div>
            <button
              onClick={onShowLogin}
              className="hidden px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:text-white sm:block"
            >
              {t.landing.signIn}
            </button>
            <button
              onClick={onShowLogin}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition-colors hover:bg-indigo-500"
            >
              {t.landing.startTrial}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <header className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-indigo-600/25 blur-3xl" />
        <div className="absolute -bottom-40 -right-20 h-[28rem] w-[28rem] rounded-full bg-blue-600/20 blur-3xl" />

        <div className="relative mx-auto max-w-5xl px-6 py-28 text-center md:py-36">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-300 backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            10K+ {t.landing.companies}
          </div>

          <h1 className="mt-8 text-5xl font-bold tracking-tight text-white md:text-6xl lg:text-7xl">
            <span className="block">{t.landing.heroTitle1}</span>
            <span className="block bg-gradient-to-r from-indigo-400 via-blue-400 to-indigo-300 bg-clip-text text-transparent">
              {t.landing.heroTitle2}
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-3xl text-lg leading-relaxed text-slate-400 md:text-xl">
            {t.landing.heroSubtitle}
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <button
              onClick={openDemo}
              className="w-full rounded-xl bg-indigo-600 px-8 py-3.5 font-semibold text-white shadow-xl shadow-indigo-600/30 transition-colors hover:bg-indigo-500 sm:w-auto"
            >
              {t.landing.startTrial}
            </button>
            <a
              href="#showcase"
              className="w-full rounded-xl border border-white/20 px-8 py-3.5 font-semibold text-white transition-colors hover:bg-white/10 sm:w-auto"
            >
              {t.landing.watchDemo}
            </a>
          </div>

          <div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-slate-400">
            {trustIndicators.map((indicator) => (
              <span key={indicator} className="flex items-center gap-2">
                <span className="text-indigo-400">✓</span>
                {indicator}
              </span>
            ))}
          </div>
        </div>
      </header>

      {/* Logo Cloud */}
      <section className="border-b border-gray-200 bg-white py-16">
        <div className="mx-auto max-w-7xl px-6">
          <p className="text-center text-sm font-medium uppercase tracking-widest text-gray-400">
            {t.landing.trustedBy}
          </p>
          <div className="mt-8 grid grid-cols-2 items-center gap-x-8 gap-y-6 sm:grid-cols-4 lg:grid-cols-8">
            {BRANDS.map((brand) => (
              <span
                key={brand}
                className="text-center text-lg font-bold tracking-tight text-gray-300 transition-colors hover:text-gray-400"
              >
                {brand}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="scroll-mt-20 bg-white py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">
              {t.landing.features}
            </p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-gray-900 md:text-4xl">
              {t.landing.featuresTitle}
            </h2>
            <p className="mt-4 text-lg text-gray-500">{t.landing.featuresSubtitle}</p>
          </div>

          <div className="mt-16 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group rounded-2xl border border-gray-200 bg-white p-8 transition-all hover:-translate-y-1 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-100/60"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-indigo-100 bg-indigo-50 text-2xl transition-transform group-hover:scale-110">
                  {feature.icon}
                </div>
                <h3 className="mt-6 text-xl font-semibold text-gray-900">{feature.title}</h3>
                <p className="mt-3 leading-relaxed text-gray-500">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="solutions" className="scroll-mt-20 border-y border-gray-200 bg-gray-50 py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">
              {t.landing.solutions}
            </p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-gray-900 md:text-4xl">
              {t.landing.howItWorksTitle}
            </h2>
            <p className="mt-4 text-lg text-gray-500">{t.landing.howItWorksSubtitle}</p>
          </div>

          <div className="relative mt-16">
            <div className="absolute left-[12.5%] right-[12.5%] top-6 hidden h-px bg-gradient-to-r from-indigo-200 via-indigo-400 to-indigo-200 md:block" />
            <div className="relative grid grid-cols-1 gap-12 md:grid-cols-4">
              {steps.map((step) => (
                <div key={step.number} className="text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 font-bold text-white shadow-lg shadow-indigo-600/30 ring-4 ring-gray-50">
                    {step.number}
                  </div>
                  <h3 className="mt-6 text-lg font-semibold text-gray-900">{step.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-gray-500">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section id="security" className="scroll-mt-20 border-b border-white/10 bg-slate-900 py-20">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-10 px-6 text-center lg:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label}>
              <div className="text-4xl font-bold tracking-tight text-white md:text-5xl">
                {stat.value}
              </div>
              <div className="mt-3 text-sm font-medium uppercase tracking-wider text-slate-400">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Product Showcase */}
      <section id="showcase" className="scroll-mt-20 bg-white py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 md:text-4xl">
              {t.landing.showcaseTitle}
            </h2>
            <p className="mt-4 text-lg text-gray-500">{t.landing.showcaseSubtitle}</p>
          </div>

          <div className="mx-auto mt-14 max-w-5xl overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl shadow-slate-300/50">
            <div className="flex items-center gap-2 border-b border-gray-200 bg-gray-100 px-4 py-3">
              <span className="h-3 w-3 rounded-full bg-red-400" />
              <span className="h-3 w-3 rounded-full bg-amber-400" />
              <span className="h-3 w-3 rounded-full bg-emerald-400" />
              <div className="ml-4 h-6 flex-1 rounded-md border border-gray-200 bg-white" />
            </div>

            <div className="relative flex h-72 items-center justify-center bg-gradient-to-br from-indigo-600 via-blue-700 to-slate-900 md:h-96">
              <div className="absolute left-0 top-0 hidden h-full w-48 border-r border-white/10 bg-white/5 p-4 md:block">
                <div className="h-3 w-24 rounded bg-white/20" />
                <div className="mt-4 h-3 w-20 rounded bg-white/10" />
                <div className="mt-3 h-3 w-24 rounded bg-white/10" />
                <div className="mt-3 h-3 w-16 rounded bg-white/10" />
              </div>
              <div className="absolute bottom-6 right-6 hidden gap-3 md:flex">
                <div className="h-20 w-8 rounded-t bg-white/10" />
                <div className="h-28 w-8 rounded-t bg-white/15" />
                <div className="h-16 w-8 rounded-t bg-white/10" />
                <div className="h-36 w-8 rounded-t bg-white/25" />
                <div className="h-24 w-8 rounded-t bg-white/15" />
              </div>
              <button
                onClick={openDemo}
                className="relative rounded-full bg-white px-8 py-3.5 font-semibold text-slate-900 shadow-xl transition-transform hover:scale-105"
              >
                {t.landing.seeInAction}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="scroll-mt-20 border-t border-gray-200 bg-gray-50 py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 md:text-4xl">
              {t.landing.pricingTitle}
            </h2>
            <p className="mt-4 text-lg text-gray-500">{t.landing.pricingSubtitle}</p>
          </div>

          <div className="mx-auto mt-16 grid max-w-6xl grid-cols-1 items-stretch gap-8 lg:grid-cols-3">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`relative rounded-2xl bg-white p-8 transition-all ${
                  plan.popular
                    ? 'border-2 border-indigo-600 shadow-2xl shadow-indigo-200/70 lg:-my-4 lg:py-12'
                    : 'border border-gray-200 shadow-sm'
                }`}
              >
                {plan.popular && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white shadow-lg">
                    {t.landing.mostPopular}
                  </span>
                )}

                <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                <div className="mt-4 flex items-end gap-1">
                  <span className="text-5xl font-bold tracking-tight text-gray-900">
                    {plan.price}
                  </span>
                  {plan.period && <span className="mb-2 text-sm text-gray-500">{plan.period}</span>}
                </div>

                <ul className="mt-8 space-y-4">
                  {plan.features.map((item) => (
                    <li key={item} className="flex items-start gap-3 text-sm text-gray-600">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-600">
                        ✓
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={onShowLogin}
                  className={`mt-8 w-full rounded-xl py-3 font-semibold transition-colors ${
                    plan.popular
                      ? 'bg-indigo-600 text-white hover:bg-indigo-500'
                      : 'border border-gray-300 bg-white text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-indigo-950 py-24">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="absolute -bottom-40 -right-20 h-96 w-96 rounded-full bg-blue-600/20 blur-3xl" />

        <div className="relative mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white md:text-5xl">
            {t.landing.finalCtaTitle}
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-400">
            {t.landing.finalCtaSubtitle}
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <button
              onClick={onShowLogin}
              className="w-full rounded-xl bg-white px-8 py-3.5 font-semibold text-slate-900 transition-colors hover:bg-slate-100 sm:w-auto"
            >
              {t.landing.startTrial}
            </button>
            <a
              href="#features"
              className="w-full rounded-xl border border-white/20 px-8 py-3.5 font-semibold text-white transition-colors hover:bg-white/10 sm:w-auto"
            >
              {t.landing.learnMore}
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-slate-950 pb-8 pt-16">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid grid-cols-2 gap-10 md:grid-cols-4 lg:grid-cols-5">
            <div className="col-span-2 lg:col-span-1">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600">
                  <span className="text-sm font-bold text-white">2TO</span>
                </div>
                <span className="text-lg font-bold tracking-tight text-white">EOS</span>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-slate-400">
                {t.landing.heroSubtitle}
              </p>
            </div>

            {footerColumns.map((column) => (
              <div key={column.title}>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
                  {column.title}
                </h3>
                <ul className="mt-4 space-y-3">
                  {column.links.map((item) => (
                    <li key={item.label}>
                      <a
                        href={item.href}
                        className="text-sm text-slate-400 transition-colors hover:text-white"
                      >
                        {item.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-14 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-8 md:flex-row">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600">
                <span className="text-[10px] font-bold text-white">2TO</span>
              </div>
              <span className="text-sm font-bold text-white">EOS</span>
            </div>
            <p className="text-sm text-slate-500">{t.landing.footerRights}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
