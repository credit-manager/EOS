import { useState, useCallback } from 'react';
import { en, ar, TranslationKeys } from './translations';

type Language = 'en' | 'ar';

const STORAGE_KEY = '2to-eos-language';

function getStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'en' || stored === 'ar') return stored;
  } catch {}
  return 'en';
}

const translations: Record<Language, TranslationKeys> = { en, ar };

export function useI18n() {
  const [language, setLanguageState] = useState<Language>(getStoredLanguage);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {}
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = lang;
  }, []);

  const t: TranslationKeys = translations[language];

  const isRTL = language === 'ar';

  return { language, setLanguage, t, isRTL };
}
