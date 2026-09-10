import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './styles.css';

function App() {
  return (
    <main className="shell">
      <section className="card">
        <p className="eyebrow">2TO</p>
        <h1>EOS ERP Platform</h1>
        <p className="lead">A clean foundation for a metadata-driven ERP platform.</p>
        <div className="status"><span />Runtime is online</div>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
