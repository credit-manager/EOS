import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import BrandedShell from './components/BrandingProvider';
import './styles/global.css';
import { initOfflineQueue } from './services/offlineQueue';

// P66: offline queue — replays saved writes when connectivity returns
initOfflineQueue();

// P66 PWA: register the service worker (production only)
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* SW registration is best-effort; app works without it */
    });
  });
}

// P67: BrandedShell replaces the previous static locale/theme wrapper.
// It loads tenant branding (if any) and applies dynamic antd tokens,
// locale, direction, and dark/light theme automatically.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrandedShell>
      <App />
    </BrandedShell>
  </React.StrictMode>
);
