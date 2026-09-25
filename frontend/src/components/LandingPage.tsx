import LanguageSwitcher from './LanguageSwitcher';
import { useI18n } from '../i18n';

export default function LandingPage({ onShowLogin }: { onShowLogin: () => void }) {
  const { language, setLanguage, isRTL, t } = useI18n();

  return (
    <div className={`min-h-screen bg-white ${isRTL ? 'rtl' : 'ltr'}`}>
      {/* Hero */}
      <header className="relative overflow-hidden">
        <nav className="flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-lg">2TO</span>
            </div>
            <span className="text-xl font-bold text-gray-900">EOS</span>
          </div>
          <div className="flex items-center gap-4">
            <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={isRTL} />
            <a href="#features" className="text-gray-600 hover:text-gray-900">{t.landing.features}</a>
            <a href="#pricing" className="text-gray-600 hover:text-gray-900">{t.landing.pricing}</a>
            <a href="#docs" className="text-gray-600 hover:text-gray-900">{t.landing.docs}</a>
            <button onClick={onShowLogin} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{t.landing.signIn}</button>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-6 py-24 text-center">
          <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6">
            {t.landing.heroTitle1}<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">
              {t.landing.heroTitle2}
            </span>
          </h1>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto mb-10">
            {t.landing.heroSubtitle}
          </p>
          <div className="flex items-center justify-center gap-4">
            <button onClick={onShowLogin} className="px-8 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 text-lg">
              {t.landing.startTrial}
            </button>
            <a href="#demo" className="px-8 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 text-lg">
              {t.landing.watchDemo}
            </a>
          </div>
        </div>
      </header>

      {/* Problem */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            {t.landing.problemTitle}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...t.landing.tools].map(tool => (
              <div key={tool} className="bg-white rounded-xl p-4 text-center border border-gray-200">
                <span className="text-gray-400 text-sm">{tool}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            {t.landing.solutionTitle}
          </h2>
          <p className="text-center text-gray-500 mb-12 max-w-2xl mx-auto">
            {t.landing.solutionSubtitle}
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            {t.landing.ctaTitle}
          </h2>
          <p className="text-blue-100 mb-8 text-lg">
            {t.landing.ctaSubtitle}
          </p>
          <button onClick={onShowLogin} className="px-8 py-3 bg-white text-blue-600 rounded-xl font-medium hover:bg-blue-50 text-lg">
            {t.landing.startTrial}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">2TO</span>
            </div>
            <span className="font-bold text-gray-900">EOS</span>
          </div>
          <p className="text-gray-400 text-sm">{t.landing.footerRights}</p>
        </div>
      </footer>
    </div>
  );
}
