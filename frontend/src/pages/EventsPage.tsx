import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';

interface Event {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  data: Record<string, unknown>;
  severity: string;
  occurred_at: string;
  created_at?: string;
}

export function EventsPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [entityFilter, setEntityFilter] = useState('all');
  const [sortNewest, setSortNewest] = useState(true);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/events', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const raw: unknown[] = json.events ?? json.items ?? json;
      if (!Array.isArray(raw)) throw new Error('Unexpected response shape');
      setEvents(raw as Event[]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load events');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const entityTypes = Array.from(new Set(events.map((e) => e.entity_type).filter(Boolean))).sort();

  const getTs = (e: Event) => e.occurred_at || e.created_at || '';

  const filtered = events
    .filter((e) => (search ? e.event_type.toLowerCase().includes(search.toLowerCase()) : true))
    .filter((e) => (entityFilter === 'all' ? true : e.entity_type === entityFilter))
    .sort((a, b) => {
      const da = new Date(getTs(a)).getTime();
      const db = new Date(getTs(b)).getTime();
      return sortNewest ? db - da : da - db;
    });

  const badgeColor = (et: string) => {
    const lower = et.toLowerCase();
    if (lower.endsWith('.created')) return 'bg-emerald-100 text-emerald-800 ring-emerald-200';
    if (lower.endsWith('.approved')) return 'bg-blue-100 text-blue-800 ring-blue-200';
    if (lower.endsWith('.updated')) return 'bg-amber-100 text-amber-800 ring-amber-200';
    if (lower.endsWith('.rejected') || lower.includes('error') || lower.includes('failed'))
      return 'bg-red-100 text-red-800 ring-red-200';
    return 'bg-gray-100 text-gray-800 ring-gray-200';
  };

  const severityDot = (sev: string) => {
    const s = sev?.toLowerCase();
    if (s === 'error' || s === 'critical') return 'bg-red-500';
    if (s === 'warning') return 'bg-amber-500';
    if (s === 'success') return 'bg-emerald-500';
    return 'bg-slate-400';
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t.eventsPage.title}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {events.length} {t.eventsPage.eventsRecorded}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              {t.eventsPage.live}
            </span>
          </div>
        </div>

        {/* Controls */}
        <div className="mb-6 flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-900/5 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
              />
            </svg>
            <input
              type="text"
              placeholder={t.eventsPage.searchPlaceholder}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-10 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <select
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          >
            <option value="all">{t.eventsPage.allEntities}</option>
            {entityTypes.map((et) => (
              <option key={et} value={et}>
                {et}
              </option>
            ))}
          </select>

          <button
            onClick={() => setSortNewest((s) => !s)}
            className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            title={t.eventsPage.sortToggleTitle}
          >
            <svg
              className={`h-4 w-4 transition-transform ${sortNewest ? '' : 'rotate-180'}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4"
              />
            </svg>
            {sortNewest ? t.eventsPage.sortNewest : t.eventsPage.sortOldest}
          </button>

          <button
            onClick={fetchEvents}
            disabled={loading}
            className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
          >
            <svg
              className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
              />
            </svg>
            {t.eventsPage.refresh}
          </button>
        </div>

        {/* Content */}
        {loading && events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <svg
              className="mb-4 h-10 w-10 animate-spin text-blue-500"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
              />
            </svg>
            <p className="text-sm text-slate-500">{t.eventsPage.loadingEvents}</p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <svg
              className="mx-auto mb-3 h-10 w-10 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
              />
            </svg>
            <p className="text-sm font-medium text-red-800">{error}</p>
            <button
              onClick={fetchEvents}
              className="mt-3 rounded-lg bg-red-100 px-4 py-1.5 text-sm font-medium text-red-700 hover:bg-red-200"
            >
              {t.eventsPage.retry}
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white py-20">
            <svg
              className="mb-4 h-12 w-12 text-slate-300"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-base font-medium text-slate-500">{t.eventsPage.noEventsFound}</p>
            <p className="mt-1 text-sm text-slate-400">
              {events.length > 0
                ? t.eventsPage.tryAdjustingFilters
                : t.eventsPage.eventsWillAppear}
            </p>
          </div>
        ) : (
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-[15px] top-0 bottom-0 w-0.5 bg-slate-200" />

            <div className="space-y-1">
              {filtered.map((event, idx) => (
                <div key={event.id ?? idx} className="relative flex gap-4">
                  {/* Dot */}
                  <div className="relative z-10 mt-5 flex h-[11px] w-[11px] shrink-0 items-center justify-center">
                    <span
                      className={`block h-3 w-3 rounded-full ring-2 ring-white ${severityDot(event.severity)}`}
                    />
                  </div>

                  {/* Card */}
                  <div className="group mb-3 flex-1 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-900/5 transition hover:shadow-md">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold ring-1 ring-inset ${badgeColor(event.event_type)}`}
                        >
                          {event.event_type}
                        </span>
                        <span className="text-xs text-slate-400" title={event.id}>
                          {event.id?.slice(0, 8)}…
                        </span>
                      </div>
                      <span className="text-xs text-slate-400">{formatTime(getTs(event))}</span>
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
                      <div>
                        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                          {t.eventsPage.entity}
                        </span>
                        <p className="truncate font-medium text-slate-700">{event.entity_type}</p>
                      </div>
                      <div>
                        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                          {t.eventsPage.entityId}
                        </span>
                        <p className="truncate font-mono text-xs text-slate-600">
                          {event.entity_id}
                        </p>
                      </div>
                      {event.severity && (
                        <div>
                          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                            {t.eventsPage.severity}
                          </span>
                          <p className="font-medium capitalize text-slate-700">{event.severity}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
