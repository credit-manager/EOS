/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f4f7fb',
          100: '#e7edf7',
          200: '#cbd8eb',
          300: '#a7bbd9',
          400: '#7896bf',
          500: '#4f70a3',
          600: '#38578c',
          700: '#2d426b',
          800: '#223052',
          900: '#18233f',
        },
        dark: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        eos: {
          success: '#15803d',
          warning: '#b45309',
          error: '#b91c1c',
          info: '#0369a1',
        },
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'IBM Plex Sans Arabic', 'Noto Sans', 'Noto Sans Arabic', 'system-ui', 'sans-serif'],
        arabic: ['IBM Plex Sans Arabic', 'Noto Sans Arabic', 'IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        eos: '0.5rem',
      },
      spacing: {
        'eos-1': '0.25rem',
        'eos-2': '0.5rem',
        'eos-3': '0.75rem',
        'eos-4': '1rem',
        'eos-5': '1.25rem',
        'eos-6': '1.5rem',
        'eos-8': '2rem',
        'eos-10': '2.5rem',
        'eos-12': '3rem',
        'eos-16': '4rem',
      },
    },
  },
  plugins: [],
}
