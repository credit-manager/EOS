import { useState, useEffect } from 'react';
import { useI18n } from '../i18n';

interface Country { id: string; code: string; name: string; currency_code: string; currency_name: string; language_code: string; language_name: string; timezone: string; }
interface Currency { id: string; code: string; name: string; symbol?: string; decimal_places: number; is_active: boolean; }
interface CountryPack { id: string; country_code: string; pack_name: string; pack_version: string; is_active: boolean; }
interface ExchangeRate { id: string; from_currency: string; to_currency: string; rate: number; rate_date: string; }

export default function GlobalizationPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [tab, setTab] = useState<'countries' | 'currencies' | 'packs' | 'rates'>('countries');
  const [countries, setCountries] = useState<Country[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [packs, setPacks] = useState<CountryPack[]>([]);
  const [rates, setRates] = useState<ExchangeRate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/globalization/countries', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/globalization/currencies', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/globalization/packs', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/globalization/exchange-rates', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([co, cu, pa, ex]) => {
      setCountries(co); setCurrencies(cu); setPacks(pa); setRates(ex);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-gray-500">{t.globalizationPage.loading}</p></div>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">{t.globalizationPage.title}</h2>
      <div className="flex gap-2 border-b border-gray-200">
        {(['countries', 'currencies', 'packs', 'rates'] as const).map(tabKey => (
          <button key={tabKey} onClick={() => setTab(tabKey)} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === tabKey ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {tabKey === 'countries' ? t.globalizationPage.tabCountries : tabKey === 'currencies' ? t.globalizationPage.tabCurrencies : tabKey === 'packs' ? t.globalizationPage.tabPacks : t.globalizationPage.tabRates}
          </button>
        ))}
      </div>

      {tab === 'countries' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {countries.map(c => (
            <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">🌍</span>
                <div>
                  <h3 className="font-semibold text-gray-900">{c.name}</h3>
                  <p className="text-xs text-gray-500">{c.code}</p>
                </div>
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <p>{t.globalizationPage.currency}: {c.currency_code} ({c.currency_name})</p>
                <p>{t.globalizationPage.language}: {c.language_name}</p>
                <p>{t.globalizationPage.timezone}: {c.timezone}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'currencies' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.code}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.name}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.symbol}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.decimals}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.active}</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {currencies.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono font-bold text-gray-900">{c.code}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.name}</td>
                  <td className="px-4 py-3 text-lg">{c.symbol || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.decimal_places}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs ${c.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{c.is_active ? t.globalizationPage.active : t.globalizationPage.inactive}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'packs' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {packs.map(p => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900">{p.pack_name}</h3>
              <p className="text-sm text-gray-500">{p.country_code} &middot; v{p.pack_version}</p>
              <span className="mt-2 inline-block px-2 py-0.5 rounded text-xs bg-green-100 text-green-700">{p.is_active ? t.globalizationPage.active : t.globalizationPage.inactive}</span>
            </div>
          ))}
          {packs.length === 0 && <p className="text-center text-gray-400 py-8 col-span-3">{t.globalizationPage.noPacksInstalled}</p>}
        </div>
      )}

      {tab === 'rates' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.from}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.to}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.rate}</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.globalizationPage.date}</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {rates.map(r => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono font-bold">{r.from_currency}</td>
                  <td className="px-4 py-3 font-mono font-bold">{r.to_currency}</td>
                  <td className="px-4 py-3 text-sm">{r.rate}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{new Date(r.rate_date).toLocaleDateString()}</td>
                </tr>
              ))}
              {rates.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No exchange rates configured</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
