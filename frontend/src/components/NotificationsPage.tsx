import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';

interface Notification {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  category: string;
  priority: string;
  is_read: boolean;
  action_url: string | null;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
}

interface NotificationStats {
  total: number;
  unread: number;
  today: number;
  this_week: number;
  by_category: Record<string, number>;
  by_type: Record<string, number>;
}

type Filter = 'all' | 'unread' | 'approvals' | 'system' | 'alerts';

export default function NotificationsPage({ token }: { token: string }) {
  const { t } = useI18n();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<NotificationStats>({ total: 0, unread: 0, today: 0, this_week: 0, by_category: {}, by_type: {} });
  const [filter, setFilter] = useState<Filter>('all');
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filter === 'unread') params.append('is_read', 'false');
      if (filter === 'approvals') params.append('category', 'approval');
      if (filter === 'system') params.append('category', 'system');
      if (filter === 'alerts') params.append('category', 'alert');

      const response = await fetch(`/api/v1/notifications?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        const items = data.items || [];
        setNotifications(items);
        const unread = items.filter((n: Notification) => !n.is_read).length;
        const today = new Date().toDateString();
        const todayCount = items.filter((n: Notification) => new Date(n.created_at).toDateString() === today).length;
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        const weekCount = items.filter((n: Notification) => new Date(n.created_at) > weekAgo).length;
        const byCategory: Record<string, number> = {};
        const byType: Record<string, number> = {};
        items.forEach((n: Notification) => {
          byCategory[n.category] = (byCategory[n.category] || 0) + 1;
          byType[n.notification_type] = (byType[n.notification_type] || 0) + 1;
        });
        setStats({ total: items.length, unread, today: todayCount, this_week: weekCount, by_category: byCategory, by_type: byType });
      }
    } catch { setError(t.notificationsPage.errorLoading); }
    finally { setLoading(false); }
  }, [filter, token, t]);

  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  const markAsRead = async (ids: string[]) => {
    try {
      await fetch('/api/v1/notifications/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ notification_ids: ids }),
      });
      fetchNotifications();
    } catch { setError(t.notificationsPage.errorMarkRead); }
  };

  const markAllAsRead = async () => {
    try {
      await fetch('/api/v1/notifications/read-all', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchNotifications();
    } catch { setError(t.notificationsPage.errorMarkAllRead); }
  };

  const handleViewNotification = (n: Notification) => {
    setSelectedNotification(n);
    if (!n.is_read) markAsRead([n.id]);
  };

  const handleDismiss = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
    if (selectedNotification?.id === id) setSelectedNotification(null);
  };

  const getPriorityColor = (p: string) => {
    const map: Record<string, string> = {
      urgent: 'border-red-300 bg-red-50',
      high: 'border-orange-200 bg-orange-50',
      medium: 'border-yellow-200 bg-yellow-50',
      low: 'border-gray-200 bg-white',
    };
    return map[p] || 'border-gray-200 bg-white';
  };

  const getCategoryIcon = (c: string) => {
    const map: Record<string, string> = { approval: '⏳', system: '⚙️', payment: '💳', project: '🏗', workflow: '⚡', alert: '🚨', document: '📄', user: '👤' };
    return map[c] || '🔔';
  };

  const getTypeIcon = (type: string) => {
    const map: Record<string, string> = { info: 'ℹ️', warning: '⚠️', error: '❌', success: '✅' };
    return map[type] || '📌';
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (minutes < 1) return t.notificationsPage.justNow;
    if (minutes < 60) return `${minutes}${t.notificationsPage.minutesAgo}`;
    if (hours < 24) return `${hours}${t.notificationsPage.hoursAgo}`;
    if (days < 7) return `${days}${t.notificationsPage.daysAgo}`;
    return date.toLocaleDateString();
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">{t.notificationsPage.title}</h1>
          {stats.unread > 0 && (
            <span className="px-3 py-1 bg-red-100 text-red-700 text-sm font-medium rounded-full">{stats.unread} {t.notificationsPage.unreadLabel}</span>
          )}
        </div>
        <div className="flex gap-2">
          {stats.unread > 0 && (
            <button onClick={markAllAsRead} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.notificationsPage.markAllRead}</button>
          )}
        </div>
      </div>

      {error && <div className="px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          [t.notificationsPage.statsTotal, stats.total, '📋', 'text-blue-600'],
          [t.notificationsPage.statsUnread, stats.unread, '🔴', 'text-red-600'],
          [t.notificationsPage.statsToday, stats.today, '📅', 'text-green-600'],
          [t.notificationsPage.statsThisWeek, stats.this_week, '📆', 'text-purple-600'],
        ].map(([label, value, icon, color]) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
            <span className="text-xl">{icon}</span>
            <p className={`text-2xl font-bold mt-1 ${color}`}>{value as number}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {([
          ['all', t.notificationsPage.filterAll, stats.total],
          ['unread', t.notificationsPage.filterUnread, stats.unread],
          ['approvals', t.notificationsPage.filterApprovals, stats.by_category.approval || 0],
          ['system', t.notificationsPage.filterSystem, stats.by_category.system || 0],
          ['alerts', t.notificationsPage.filterAlerts, stats.by_category.alert || 0],
        ] as const).map(([key, label, count]) => (
          <button key={key} onClick={() => setFilter(key)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${filter === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {label} ({count})
          </button>
        ))}
      </div>

      {/* Notification List + Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List */}
        <div className={`space-y-2 ${selectedNotification ? 'lg:col-span-1' : 'lg:col-span-3'}`}>
          {notifications.map(n => (
            <div
              key={n.id}
              onClick={() => handleViewNotification(n)}
              className={`rounded-xl border p-4 cursor-pointer transition-all ${getPriorityColor(n.priority)} ${!n.is_read ? 'ring-2 ring-blue-200' : ''} ${selectedNotification?.id === n.id ? 'ring-2 ring-blue-400' : ''}`}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl shrink-0">{getCategoryIcon(n.category)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {!n.is_read && <span className="w-2 h-2 bg-blue-500 rounded-full shrink-0" />}
                    <h3 className="text-sm font-semibold text-gray-900 truncate">{n.title}</h3>
                    <span className="text-xs text-gray-400 shrink-0">{formatTime(n.created_at)}</span>
                  </div>
                  <p className="text-xs text-gray-600 line-clamp-2">{n.message}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${n.category === 'approval' ? 'bg-purple-100 text-purple-700' : n.category === 'system' ? 'bg-gray-100 text-gray-700' : n.category === 'payment' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>{n.category}</span>
                    <span className="text-xs text-gray-400">{getTypeIcon(n.notification_type)} {n.notification_type}</span>
                  </div>
                </div>
                <button onClick={e => { e.stopPropagation(); handleDismiss(n.id); }} className="text-gray-400 hover:text-gray-600 shrink-0">&times;</button>
              </div>
            </div>
          ))}
          {notifications.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-4xl mb-3">🔔</p>
              <p className="font-medium">{t.notificationsPage.noNotifications}</p>
              <p className="text-sm">{t.notificationsPage.allCaughtUp}</p>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selectedNotification && (
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6 sticky top-6 self-start">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{getCategoryIcon(selectedNotification.category)}</span>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{selectedNotification.title}</h2>
                  <p className="text-xs text-gray-500">{formatTime(selectedNotification.created_at)}</p>
                </div>
              </div>
              <button onClick={() => setSelectedNotification(null)} className="text-gray-400 hover:text-gray-600">&times;</button>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${selectedNotification.category === 'approval' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}`}>{selectedNotification.category}</span>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${selectedNotification.notification_type === 'error' ? 'bg-red-100 text-red-800' : selectedNotification.notification_type === 'warning' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}`}>{selectedNotification.notification_type}</span>
              {selectedNotification.priority && <span className={`px-2 py-1 text-xs font-medium rounded-full ${selectedNotification.priority === 'urgent' ? 'bg-red-100 text-red-800' : selectedNotification.priority === 'high' ? 'bg-orange-100 text-orange-800' : 'bg-gray-100 text-gray-800'}`}>{selectedNotification.priority}</span>}
            </div>
            <div className="prose prose-sm max-w-none mb-4">
              <p className="text-gray-700 leading-relaxed">{selectedNotification.message}</p>
            </div>
            {selectedNotification.entity_type && (
              <div className="p-3 bg-gray-50 rounded-lg mb-4">
                <p className="text-xs text-gray-500">{t.notificationsPage.relatedEntity}</p>
                <p className="text-sm font-medium">{selectedNotification.entity_type} &middot; {selectedNotification.entity_id}</p>
              </div>
            )}
            <div className="flex gap-3 pt-4 border-t border-gray-100">
              {selectedNotification.action_url && (
                <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{t.notificationsPage.viewRelated}</button>
              )}
              {!selectedNotification.is_read && (
                <button onClick={() => markAsRead([selectedNotification.id])} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.notificationsPage.markAsRead}</button>
              )}
              <button onClick={() => { handleDismiss(selectedNotification.id); }} className="px-4 py-2 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100">{t.notificationsPage.dismiss}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
