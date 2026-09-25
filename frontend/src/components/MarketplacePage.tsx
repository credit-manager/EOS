import { useState, useEffect } from 'react';
import { useI18n } from '../i18n';

interface MarketplaceApp { id: string; code: string; name: string; short_description?: string; app_type: string; category: string; author: string; version: string; pricing_model: string; price?: number; rating?: number; rating_count: number; install_count: number; is_featured: boolean; tags?: string[]; }
interface MarketplaceCategory { id: string; code: string; name: string; description?: string; icon?: string; }
interface MarketplaceStats { total_apps: number; total_categories: number; total_installs: number; total_reviews: number; }

export default function MarketplacePage({ token }: { token: string }) {
  const { t } = useI18n();
  const [apps, setApps] = useState<MarketplaceApp[]>([]);
  const [categories, setCategories] = useState<MarketplaceCategory[]>([]);
  const [stats, setStats] = useState<MarketplaceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/marketplace/apps', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/marketplace/categories', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch('/api/v1/marketplace/stats', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([a, c, s]) => {
      setApps(a); setCategories(c); setStats(s);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token]);

  const handleSearch = async () => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (selectedCategory) params.set('category', selectedCategory);
    const r = await fetch(`/api/v1/marketplace/apps?${params}`, { headers: { Authorization: `Bearer ${token}` } });
    setApps(await r.json());
  };

  const pricingBadge = (m: string, p?: number) => {
    if (m === 'free') return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">{t.marketplacePage.free}</span>;
    if (m === 'paid') return <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">${p}</span>;
    if (m === 'freemium') return <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">{t.marketplacePage.freemium}</span>;
    return <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{m}</span>;
  };

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-gray-500">{t.marketplacePage.loading}</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.marketplacePage.title}</h2>
          <p className="text-sm text-gray-500">{t.marketplacePage.subtitle}</p>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: t.marketplacePage.apps, value: stats.total_apps, icon: '📦' },
            { label: t.marketplacePage.categories, value: stats.total_categories, icon: '📂' },
            { label: t.marketplacePage.installs, value: stats.total_installs, icon: '⬇' },
            { label: t.marketplacePage.reviews, value: stats.total_reviews, icon: '⭐' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
              <span className="text-2xl">{s.icon}</span>
              <div>
                <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                <p className="text-sm text-gray-500">{s.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        <input
          type="text"
          placeholder={t.marketplacePage.searchPlaceholder}
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        <select value={selectedCategory} onChange={e => setSelectedCategory(e.target.value)} className="px-4 py-2 border border-gray-300 rounded-lg">
          <option value="">{t.marketplacePage.allCategories}</option>
          {categories.map(c => <option key={c.id} value={c.code}>{c.name}</option>)}
        </select>
        <button onClick={handleSearch} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{t.marketplacePage.search}</button>
      </div>

      {categories.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {categories.map(c => (
            <button key={c.id} onClick={() => { setSelectedCategory(c.code); handleSearch(); }} className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-300">
              {c.icon} {c.name}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {apps.map(app => (
          <div key={app.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white text-lg font-bold">
                  {app.name[0]}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{app.name}</h3>
                  <p className="text-xs text-gray-500">{t.marketplacePage.by} {app.author}</p>
                </div>
              </div>
              {app.is_featured && <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">{t.marketplacePage.featured}</span>}
            </div>
            <p className="text-sm text-gray-600 mb-3 line-clamp-2">{app.short_description || t.marketplacePage.noDescription}</p>
            <div className="flex items-center justify-between">
              <div className="flex gap-2 text-xs">
                <span className="px-2 py-0.5 bg-gray-100 rounded">{app.category}</span>
                {pricingBadge(app.pricing_model, app.price)}
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                {app.rating != null && <span>⭐ {app.rating.toFixed(1)}</span>}
                <span>📥 {app.install_count}</span>
              </div>
            </div>
            {app.tags && app.tags.length > 0 && (
              <div className="mt-3 flex gap-1 flex-wrap">
                {app.tags.slice(0, 3).map(tag => (
                  <span key={tag} className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">{tag}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {apps.length === 0 && (
          <div className="col-span-3 text-center py-12">
            <p className="text-gray-400 text-lg">{t.marketplacePage.noAppsFound}</p>
            <p className="text-gray-400 text-sm mt-1">{t.marketplacePage.tryAdjusting}</p>
          </div>
        )}
      </div>
    </div>
  );
}
