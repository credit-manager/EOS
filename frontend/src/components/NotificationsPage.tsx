import React, { useState, useEffect } from 'react';
import { TranslationKeys } from '../i18n';
import DataTable from './DataTable';

interface Notification {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  category: string;
  is_read: boolean;
  action_url: string | null;
  created_at: string;
}

interface NotificationsPageProps {
  t: TranslationKeys;
  token: string;
}

export default function NotificationsPage({ t: _t, token }: NotificationsPageProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [, setShowModal] = useState(false);
  const [, setSelectedNotification] = useState<Notification | null>(null);

  useEffect(() => {
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const fetchNotifications = async () => {
    try {
      const response = await fetch(
        `/api/v1/notifications?is_read=${filter === 'unread' ? 'false' : ''}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (response.ok) {
        const data = await response.json();
        setNotifications(data.items || []);
        setUnreadCount(data.unread_count || 0);
      }
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRead = async (id: string) => {
    try {
      await fetch(`/api/v1/notifications/read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ notification_ids: [id] }),
      });
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark as read:', err);
    }
  };

  const handleReadAll = async () => {
    try {
      await fetch(`/api/v1/notifications/read-all`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const handleView = (notification: Notification) => {
    setSelectedNotification(notification);
    setShowModal(true);
    if (!notification.is_read) {
      handleRead(notification.id);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          {unreadCount > 0 && (
            <span className="px-2 py-1 bg-red-100 text-red-700 text-sm font-medium rounded-full">
              {unreadCount} unread
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as 'all' | 'unread')}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="unread">Unread Only</option>
          </select>
          {unreadCount > 0 && (
            <button onClick={handleReadAll} className="btn-secondary">
              Mark All Read
            </button>
          )}
        </div>
      </div>

      <DataTable
        data={notifications}
        columns={[
          { key: 'title', header: 'Title', className: 'max-w-xs truncate' },
          {
            key: 'message',
            header: 'Message',
            className: 'max-w-md truncate',
            render: (row: Notification) => (
              <span className="text-sm text-gray-600 max-w-md truncate block">{row.message}</span>
            ),
          },
          {
            key: 'notification_type',
            header: 'Type',
            render: (row: Notification) => <TypeBadge type={row.notification_type} />,
          },
          {
            key: 'category',
            header: 'Category',
            render: (row: Notification) => <CategoryBadge category={row.category} />,
          },
          {
            key: 'created_at',
            header: 'Date',
            render: (row: Notification) => formatDate(row.created_at),
            className: 'whitespace-nowrap',
          },
          {
            key: 'is_read',
            header: 'Read',
            render: (row: Notification) => (
              <span className={row.is_read ? 'text-green-600' : 'text-yellow-600'}>
                {row.is_read ? '✓ Read' : '○ Unread'}
              </span>
            ),
          },
        ]}
        onEdit={handleView}
        onDelete={() => {}}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        t={{} as any}
      />
    </div>
  );
}

function TypeBadge({ type }: { type: string }) {
  const typeMap: Record<string, { label: string; class: string }> = {
    info: { label: 'Info', class: 'bg-blue-100 text-blue-800' },
    warning: { label: 'Warning', class: 'bg-yellow-100 text-yellow-800' },
    error: { label: 'Error', class: 'bg-red-100 text-red-800' },
    success: { label: 'Success', class: 'bg-green-100 text-green-800' },
  };
  const s = typeMap[type] || { label: type, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function CategoryBadge({ category }: { category: string }) {
  const catMap: Record<string, { label: string; class: string }> = {
    system: { label: 'System', class: 'bg-gray-100 text-gray-800' },
    approval: { label: 'Approval', class: 'bg-purple-100 text-purple-800' },
    payment: { label: 'Payment', class: 'bg-green-100 text-green-800' },
    project: { label: 'Project', class: 'bg-blue-100 text-blue-800' },
    workflow: { label: 'Workflow', class: 'bg-orange-100 text-orange-800' },
  };
  const s = catMap[category] || { label: category, class: 'bg-gray-100 text-gray-800' };
  return <span className={`px-2 py-1 text-xs font-medium rounded-full ${s.class}`}>{s.label}</span>;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('ar-SA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
