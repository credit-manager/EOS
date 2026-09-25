import { useState } from 'react';
import LanguageSwitcher from './LanguageSwitcher';
import { useI18n } from '../i18n';

interface OnboardingWizardProps {
  onComplete: () => void;
}

type Step = 'welcome' | 'company' | 'industry' | 'invite' | 'complete';

export default function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const { language, setLanguage, isRTL, t } = useI18n();
  const [step, setStep] = useState<Step>('welcome');
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [inviteEmails, setInviteEmails] = useState('');

  const steps: Step[] = ['welcome', 'company', 'industry', 'invite', 'complete'];
  const currentIdx = steps.indexOf(step);

  return (
    <div className={`min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4 ${isRTL ? 'rtl' : 'ltr'}`}>
      <div className="max-w-2xl w-full">
        <div className="flex justify-end mb-4">
          <LanguageSwitcher language={language} onSwitch={setLanguage} isRTL={isRTL} />
        </div>
        <div className="flex items-center gap-2 mb-8">
          {steps.map((s, i) => (
            <div key={s} className={`h-2 flex-1 rounded-full transition-colors ${
              i <= currentIdx ? 'bg-blue-600' : 'bg-gray-200'
            }`} />
          ))}
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          {step === 'welcome' && (
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <span className="text-white text-3xl font-bold">2TO</span>
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-3">{t.onboard.welcomeTitle}</h1>
              <p className="text-gray-500 mb-8">{t.onboard.welcomeSubtitle}</p>
              <button onClick={() => setStep('company')}
                className="px-8 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">
                {t.onboard.getStarted}
              </button>
            </div>
          )}

          {step === 'company' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{t.onboard.companyName}</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t.onboard.companyName}</label>
                  <input value={companyName} onChange={e => setCompanyName(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500"
                    placeholder={t.onboard.companyNamePlaceholder} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t.onboard.industry}</label>
                  <select value={industry} onChange={e => setIndustry(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500">
                    <option value="">{t.onboard.industryPlaceholder}</option>
                    <option value="construction">Construction</option>
                    <option value="trading">Trading & Distribution</option>
                    <option value="manufacturing">Manufacturing</option>
                    <option value="professional_services">Professional Services</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="real_estate">Real Estate</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end mt-8">
                <button onClick={() => setStep('industry')} disabled={!companyName}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">
                  {t.common.next}
                </button>
              </div>
            </div>
          )}

          {step === 'industry' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{t.onboard.industry}</h2>
              <div className="flex justify-end mt-8">
                <button onClick={() => setStep('invite')}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">
                  {t.common.next}
                </button>
              </div>
            </div>
          )}

          {step === 'invite' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{t.onboard.inviteTeam}</h2>
              <textarea value={inviteEmails} onChange={e => setInviteEmails(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 h-32"
                placeholder={t.onboard.invitePlaceholder} />
              <div className="flex justify-between mt-8">
                <button onClick={() => setStep('complete')} className="px-6 py-2.5 text-gray-600 font-medium hover:text-gray-900">
                  {t.common.skip || 'Skip'}
                </button>
                <button onClick={() => setStep('complete')}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">
                  {t.common.next}
                </button>
              </div>
            </div>
          )}

          {step === 'complete' && (
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-green-600 text-3xl">🎉</span>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{t.onboard.completeTitle}</h2>
              <p className="text-gray-500 mb-8">{t.onboard.completeSubtitle}</p>
              <button onClick={onComplete}
                className="px-8 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">
                {t.onboard.goToDashboard}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
