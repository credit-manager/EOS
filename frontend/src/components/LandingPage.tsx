import { useEffect, useState } from 'react';
import LanguageSwitcher from './LanguageSwitcher';
import { useI18n } from '../i18n';
import Reveal from './landing/Reveal';
import CommandCenter from './landing/CommandCenter';
import ArchitectureSection from './landing/ArchitectureSection';
import AIWorkforceSection from './landing/AIWorkforceSection';
import AdoptionSection from './landing/AdoptionSection';

type LandingProps = { onShowLogin: () => void };

function Logo({ size = 'md' }: { size?: 'md' | 'sm' }) {
  const box = size === 'md' ? 'h-9 w-9 text-sm' : 'h-7 w-7 text-[10px]';
  return (
    <span className="flex items-center gap-2.5">
      <span className={`flex items-center justify-center rounded-lg bg-blue-600 font-bold text-white shadow-sm shadow-blue-600/40 ${box}`}>
        2TO
      </span>
      <span className={`font-bold tracking-tight text-white ${size === 'md' ? 'text-lg' : 'text-sm'}`}>
        EOS
      </span>
    </span>
  );
}

function ArrowDownIcon() {
  return (
    <svg className="h-4 w-4 animate-bounce" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 15a1 1 0 0 1-.7-.3l-5-5a1 1 0 0 1 1.4-1.4L10 12.6l4.3-4.3a1 1 0 1 1 1.4 1.4l-5 5a1 1 0 0 1-.7.3Z" />
    </svg>
  );
}

function FeatureIcon({ name }: { name: 'shield' | 'scale' | 'key' | 'doc' | 'layers' | 'lock' }) {
  const paths: Record<string, string> = {
    shield: 'M10 1.5 3.5 4v5c0 4 2.8 7.6 6.5 8.5 3.7-.9 6.5-4.5 6.5-8.5V4L10 1.5Zm0 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4Z',
    scale: 'M10 2a1.5 1.5 0 0 1 1.5 1.5V5h4.8a1 1 0 0 1 1 1.3l-1.7 5.7a3 3 0 0 1-2.9 2.2h-3.6a3 3 0 0 1-2.9-2.2L3.7 6.3a1 1 0 0 1 1-1h4.8v-1.5A1.5 1.5 0 0 1 10 2Zm-4.4 8.7a1 1 0 0 0 .7.3h7.4a1 1 0 0 0 .7-.3L15.1 7H4.9l.7 3.7ZM3 16.5A1.5 1.5 0 0 1 4.5 15h11a1.5 1.5 0 0 1 0 3h-11A1.5 1.5 0 0 1 3 16.5Z',
    key: 'M14.5 2a5.5 5.5 0 0 0-5.2 7.3L2 16.6V19h2.4l1-1h1.8v-1.8h1.8l1.1-1.1A5.5 5.5 0 1 0 14.5 2Zm1.8 5.4a1.4 1.4 0 1 1-2 0 1.4 1.4 0 0 1 2 0Z',
    doc: 'M6 2h5.6L17 7.4V17a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 5 17V3.5A1.5 1.5 0 0 1 6.5 2H6Zm7 4.5L11.5 4H7v12h9V7.5h-1.5ZM8 10h5v1.4H8V10Zm0 3h5v1.4H8V13Z',
    layers: 'M10 2.5 2.5 6.4 10 10.3l7.5-3.9L10 2.5ZM3.9 9.1 2.5 9.8 10 13.7l7.5-3.9-1.4-.7L10 12.3 3.9 9.1ZM3.9 12.4l-1.4.7L10 17l7.5-3.9-1.4-.7L10 15.6l-6.1-3.2Z',
    lock: 'M10 1.5A4 4 0 0 0 6 5.5v2H5.5A1.5 1.5 0 0 0 4 9v7.5A1.5 1.5 0 0 0 5.5 18h9a1.5 1.5 0 0 0 1.5-1.5V9a1.5 1.5 0 0 0-1.5-1.5H10v-2a4 4 0 0 0-4-4Zm2.4 6.5H8v-2a2 2 0 1 1 4 4v-2Z',
  };
  return (
    <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d={paths[name]} fillRule="evenodd" clipRule="evenodd" />
    </svg>
  );
}

export default function LandingPage({ onShowLogin }: LandingProps) {
  const { language, setLanguage, isRTL, t } = useI18n();
  const openDemo = () => {
    window.location.href = `${window.location.pathname}?demo=1`;
  };
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const navLinks = [
    { label: t.landing.navPlatform, href: '#command-center' },
    { label: t.landing.navIndustries, href: '#architecture' },
    { label: t.landing.navAiWorkforce, href: '#ai' },
    { label: t.landing.navResources, href: '#trust' },
  ];

  const automationSteps = [
    { title: t.landing.autoStep1, desc: t.landing.autoStep1Desc },
    { title: t.landing.autoStep2, desc: t.landing.autoStep2Desc },
    { title: t.landing.autoStep3, desc: t.landing.autoStep3Desc },
    { title: t.landing.autoStep4, desc: t.landing.autoStep4Desc },
    { title: t.landing.autoStep5, desc: t.landing.autoStep5Desc },
  ];

  const trustItems = [
    { icon: 'shield' as const, title: t.landing.trustSecurity, desc: t.landing.trustSecurityDesc },
    { icon: 'scale' as const, title: t.landing.trustGovernance, desc: t.landing.trustGovernanceDesc },
    { icon: 'key' as const, title: t.landing.trustPermissions, desc: t.landing.trustPermissionsDesc },
    { icon: 'doc' as const, title: t.landing.trustAudit, desc: t.landing.trustAuditDesc },
    { icon: 'layers' as const, title: t.landing.trustScalability, desc: t.landing.trustScalabilityDesc },
    { icon: 'lock' as const, title: t.landing.trustTenantIsolation, desc: t.landing.trustTenantIsolationDesc },
  ];

  const footerColumns = [
    {
      title: t.landing.footerProduct,
      links: [
        { label: t.landing.footerLinkPlatform, href: '#command-center' },
        { label: t.landing.navAiWorkforce, href: '#ai' },
        { label: t.landing.archTitle, href: '#architecture' },
        { label: t.landing.footerLinkPricing, href: '#adoption' },
      ],
    },
    {
      title: t.landing.footerCompany,
      links: [
        { label: t.landing.footerLinkAbout, href: '#' },
        { label: t.landing.footerLinkCareers, href: '#' },
        { label: t.landing.footerLinkContact, href: '#' },
        { label: t.landing.footerLinkBlog, href: '#' },
      ],
    },
    {
      title: t.landing.footerResources,
      links: [
        { label: t.landing.footerLinkDocs, href: '#' },
        { label: t.landing.footerLinkApi, href: '#' },
        { label: t.landing.footerLinkSupport, href: '#' },
        { label: t.landing.footerLinkStatus, href: '#' },
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

  return (
    <div className={`min-h-screen bg-white ${isRTL ? 'rtl' : 'ltr'}`}>
      {/* Navigation */}
      <nav
        className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
          scrolled ? 'border-b border-white/10 bg-slate-950/85 backdrop-blur-xl' : 'bg-transparent'
        }`}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <a href="#top" aria-label="2TO EOS">
            <Logo />
          </a>

          <div className="hidden items-center gap-7 lg:flex">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-white/10 p-0.5 backdrop-blur">
              <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={isRTL} />
            </div>
            <button
              onClick={onShowLogin}
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:text-white sm:block"
            >
              {t.landing.signIn}
            </button>
            <button
              onClick={onShowLogin}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-600/40 transition-colors hover:bg-blue-500"
            >
              {t.landing.requestAccess}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <header id="top" className="hero-noise relative overflow-hidden bg-slate-950 pt-32 pb-20 md:pt-40 md:pb-28">
        <div className="absolute inset-0 hero-grid" aria-hidden="true" />
        <div
          className="absolute -top-40 left-1/2 h-[32rem] w-[52rem] -translate-x-1/2 rounded-full bg-blue-600/20 blur-[120px]"
          aria-hidden="true"
        />
        <div
          className="absolute -bottom-52 -right-32 h-96 w-96 rounded-full bg-indigo-600/15 blur-[100px]"
          aria-hidden="true"
        />

        <div className="relative mx-auto max-w-4xl px-6 text-center">
          <Reveal>
            <span className="inline-flex items-center gap-2.5 rounded-full border border-white/12 bg-white/5 px-4 py-1.5 text-xs font-medium text-slate-300 backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.9)]" />
              <span className="font-semibold tracking-wide text-white">{t.landing.heroEyebrow}</span>
              <span className="h-3 w-px bg-white/15" />
              {t.landing.heroBadge}
            </span>
          </Reveal>

          <Reveal delay={90}>
            <h1 className="mt-7 text-4xl font-bold leading-[1.08] tracking-tight text-white sm:text-5xl md:text-6xl lg:text-7xl">
              {t.landing.heroTitle}
            </h1>
          </Reveal>

          <Reveal delay={170}>
            <p className="mx-auto mt-6 max-w-3xl text-base leading-relaxed text-slate-400 md:text-lg">
              {t.landing.heroSubtitleNew}
            </p>
          </Reveal>

          <Reveal delay={240}>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <button
                onClick={openDemo}
                className="w-full rounded-xl bg-blue-600 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 transition-all hover:-translate-y-0.5 hover:bg-blue-500 sm:w-auto"
              >
                {t.landing.heroCtaPrimary}
              </button>
              <a
                href="#command-center"
                className="w-full rounded-xl border border-white/15 bg-white/5 px-7 py-3.5 text-sm font-semibold text-white backdrop-blur transition-all hover:-translate-y-0.5 hover:bg-white/10 sm:w-auto"
              >
                {t.landing.heroCtaSecondary}
              </a>
            </div>
          </Reveal>

          <Reveal delay={320}>
            <div className="mt-8 flex items-center justify-center gap-2 text-xs text-slate-500">
              <ArrowDownIcon />
              {t.landing.heroScroll}
            </div>
          </Reveal>
        </div>
      </header>

      {/* Command Center */}
      <section id="command-center" className="relative scroll-mt-20 overflow-hidden bg-gradient-to-b from-slate-950 via-slate-50 to-white pb-24 pt-4 md:pb-32">
        <div className="mx-auto -mt-14 max-w-6xl px-6 md:-mt-20">
          <Reveal>
            <CommandCenter />
          </Reveal>
        </div>
        <Reveal delay={120} className="mx-auto mt-10 max-w-3xl px-6 text-center">
          <p className="text-sm leading-relaxed text-slate-500">{t.landing.dashSubtitle}</p>
          <button
            onClick={openDemo}
            className="mt-6 inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-900 shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-400 hover:text-blue-700"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M6.3 3.6a1 1 0 0 1 1-.7h5.4a1 1 0 0 1 1 .7l1.8 5.4H4.5l1.8-5.4Zm-2.8 7.4h13a1 1 0 0 1 0 2H3.5a1 1 0 0 1 0-2ZM3.2 15a1 1 0 0 1 1-1h11.6a1 1 0 1 1 0 2H4.2a1 1 0 0 1-1-1Z" />
            </svg>
            {t.landing.seeInAction}
          </button>
        </Reveal>
      </section>

      {/* Architecture */}
      <ArchitectureSection />

      {/* AI Workforce */}
      <AIWorkforceSection />

      {/* Automation */}
      <section id="automation" className="scroll-mt-20 border-y border-slate-200 bg-slate-50 py-24 md:py-32">
        <div className="mx-auto max-w-7xl px-6">
          <Reveal className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">
              {t.landing.dashAutomation}
            </p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-slate-900 md:text-5xl">
              {t.landing.autoTitle}
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-slate-500">{t.landing.autoSubtitle}</p>
          </Reveal>

          <div className="mt-14 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-5">
            {automationSteps.map((step, index) => (
              <Reveal key={step.title} delay={index * 80} className="relative">
                <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-blue-300 hover:shadow-lg hover:shadow-blue-100/60">
                  <div className="flex items-center justify-between">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white">
                      {index + 1}
                    </span>
                    <span className="text-2xl font-bold tracking-tight text-slate-200">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                  </div>
                  <h3 className="mt-5 text-base font-semibold text-slate-900">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-500">{step.desc}</p>
                </div>
                {index < automationSteps.length - 1 && (
                  <span className="absolute -bottom-4 left-1/2 hidden -translate-x-1/2 lg:block">
                    <span className="h-2 w-2 rounded-full bg-blue-500" />
                  </span>
                )}
              </Reveal>
            ))}
          </div>

          <Reveal delay={160}>
            <div className="mx-auto mt-10 flex max-w-3xl items-start gap-4 rounded-xl border border-blue-200 bg-blue-50 p-6">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white">
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path d="M11.3 1.5a.8.8 0 0 1 1.4 0l1 3.1a.8.8 0 0 0 .6.6l3.1 1a.8.8 0 0 1 0 1.4l-3.1 1a.8.8 0 0 0-.6.6l-1 3.1a.8.8 0 0 1-1.4 0l-1-3.1a.8.8 0 0 0-.6-.6l-3.1-1a.8.8 0 0 1 0-1.4l3.1-1a.8.8 0 0 0 .6-.6l1-3.1ZM4 11.5a.8.8 0 0 1 1.1.3l.7 1.9.2.2 1.9.7a.8.8 0 0 1 0 1.4l-1.9.7-.2.2-.7 1.9a.8.8 0 0 1-1.4 0l-.7-1.9-.2-.2-1.9-.7a.8.8 0 0 1 0-1.4l1.9-.7.2-.2.7-1.9a.8.8 0 0 1 .3-.3Z" />
                </svg>
              </span>
              <p className="text-sm leading-relaxed text-blue-900">{t.landing.autoNote}</p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Enterprise Trust */}
      <section id="trust" className="relative scroll-mt-20 overflow-hidden bg-slate-950 py-24 md:py-32">
        <div className="absolute inset-0 hero-grid" aria-hidden="true" />
        <div
          className="absolute -top-32 right-0 h-80 w-80 rounded-full bg-blue-600/15 blur-[100px]"
          aria-hidden="true"
        />

        <div className="relative mx-auto max-w-7xl px-6">
          <Reveal className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-500">
              {t.landing.footerLinkSecurity}
            </p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
              {t.landing.trustTitle}
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-slate-400">{t.landing.trustSubtitle}</p>
          </Reveal>

          <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {trustItems.map((item, index) => (
              <Reveal key={item.title} delay={index * 70}>
                <div className="group h-full rounded-xl border border-white/8 bg-white/[0.03] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-blue-500/40 hover:bg-white/[0.05]">
                  <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-blue-500/30 bg-blue-500/10 text-blue-400 transition-colors group-hover:bg-blue-500/20">
                    <FeatureIcon name={item.icon} />
                  </span>
                  <h3 className="mt-5 text-base font-semibold text-white">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal delay={140}>
            <div className="mx-auto mt-10 max-w-3xl rounded-xl border border-blue-500/25 bg-blue-500/10 p-6 text-center text-sm leading-relaxed text-blue-200">
              {t.landing.trustAiGovernanceDesc}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Platform Adoption */}
      <AdoptionSection onShowLogin={onShowLogin} />

      {/* Final CTA */}
      <section className="hero-noise relative overflow-hidden bg-slate-950 py-24 md:py-28">
        <div className="absolute inset-0 hero-grid" aria-hidden="true" />
        <div
          className="absolute -bottom-40 left-1/2 h-96 w-[44rem] -translate-x-1/2 rounded-full bg-blue-600/20 blur-[110px]"
          aria-hidden="true"
        />

        <div className="relative mx-auto max-w-3xl px-6 text-center">
          <Reveal>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-500">
              {t.landing.ctaEyebrow}
            </p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
              {t.landing.ctaHeading}
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-slate-400 md:text-lg">
              {t.landing.ctaDesc}
            </p>
          </Reveal>

          <Reveal delay={120}>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <button
                onClick={onShowLogin}
                className="w-full rounded-xl bg-blue-600 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 transition-all hover:-translate-y-0.5 hover:bg-blue-500 sm:w-auto"
              >
                {t.landing.ctaPrimary}
              </button>
              <button
                onClick={onShowLogin}
                className="w-full rounded-xl border border-white/15 bg-white/5 px-7 py-3.5 text-sm font-semibold text-white backdrop-blur transition-all hover:-translate-y-0.5 hover:bg-white/10 sm:w-auto"
              >
                {t.landing.ctaSecondary}
              </button>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-slate-950 pb-8 pt-16">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid grid-cols-2 gap-10 md:grid-cols-4 lg:grid-cols-6">
            <div className="col-span-2 lg:col-span-2">
              <Logo />
              <p className="mt-4 text-sm font-medium text-slate-300">{t.landing.footerTagline}</p>
              <p className="mt-3 max-w-sm text-sm leading-relaxed text-slate-500">{t.landing.footerDesc}</p>
            </div>

            {footerColumns.map((column) => (
              <div key={column.title}>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
                  {column.title}
                </h3>
                <ul className="mt-4 space-y-2.5">
                  {column.links.map((item) => (
                    <li key={item.label}>
                      <a
                        href={item.href}
                        className="text-sm text-slate-500 transition-colors hover:text-white"
                      >
                        {item.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-14 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-7 md:flex-row">
            <p className="text-xs text-slate-600">{t.landing.footerRights}</p>
            <div className="flex items-center gap-4 text-xs text-slate-600">
              <a href="#top" className="transition-colors hover:text-slate-400">
                {t.landing.footerSystemStatus}
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
