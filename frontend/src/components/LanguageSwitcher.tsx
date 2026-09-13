import React from 'react';

interface LanguageSwitcherProps {
  language: 'en' | 'ar';
  onSwitch: (lang: 'en' | 'ar') => void;
  isRTL: boolean;
}

export default function LanguageSwitcher({ language, onSwitch, isRTL }: LanguageSwitcherProps) {
  return (
    <button
      onClick={() => onSwitch(language === 'en' ? 'ar' : 'en')}
      className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors`}
    >
      <span>🌐</span>
      <span>{language === 'en' ? 'عربي' : 'English'}</span>
    </button>
  );
}
