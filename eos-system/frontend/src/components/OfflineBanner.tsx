/**
 * EOS System — Offline Banner (P66)
 * Shows connection state and pending offline operations count.
 */

import React, { useEffect, useState } from 'react';
import { Alert, Tag } from 'antd';
import {
  DisconnectOutlined as CloudOfflineOutlined,
  CloudUploadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import {
  getQueueSize,
  EV_QUEUE_CHANGED,
  EV_SYNC_DONE,
} from '../services/offlineQueue';

const OfflineBanner: React.FC = () => {
  const online = useNetworkStatus();
  const [pending, setPending] = useState<number>(() => getQueueSize());
  const [justSynced, setJustSynced] = useState<number>(0);

  useEffect(() => {
    const onQueueChanged = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setPending(detail?.size ?? getQueueSize());
    };
    const onSyncDone = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.synced > 0) {
        setJustSynced(detail.synced);
        setTimeout(() => setJustSynced(0), 6000);
      }
      setPending(detail?.remaining ?? getQueueSize());
    };

    window.addEventListener(EV_QUEUE_CHANGED, onQueueChanged);
    window.addEventListener(EV_SYNC_DONE, onSyncDone);
    return () => {
      window.removeEventListener(EV_QUEUE_CHANGED, onQueueChanged);
      window.removeEventListener(EV_SYNC_DONE, onSyncDone);
    };
  }, []);

  // Sync success toast line
  if (online && justSynced > 0 && pending === 0) {
    return (
      <Alert
        type="success"
        showIcon
        icon={<CloudUploadOutlined />}
        message={`تمت مزامنة ${justSynced} عملية مع السيرفر`}
        style={{ marginBottom: 12 }}
      />
    );
  }

  if (!online) {
    return (
      <Alert
        type="warning"
        showIcon
        icon={<CloudOfflineOutlined />}
        message="لا يوجد اتصال بالإنترنت — وضع عدم الاتصال"
        description={
          pending > 0 ? (
            <span>
              لديك{' '}
              <Tag color="orange" style={{ margin: 0 }}>
                <SyncOutlined /> {pending}
              </Tag>{' '}
              عملية محفوظة وسيتم إرسالها تلقائيًا عند عودة الاتصال. تصفح البيانات المحفوظة بحرية.
            </span>
          ) : (
            <span>يمكنك تصفح آخر البيانات المحفوظة، وسيتم حفظ أي عملية جديدة وإرسالها تلقائيًا.</span>
          )
        }
        style={{ marginBottom: 12 }}
      />
    );
  }

  // Online but some queued ops still waiting replay
  if (online && pending > 0) {
    return (
      <Alert
        type="info"
        showIcon
        icon={<SyncOutlined spin />}
        message={`جاري مزامنة ${pending} عملية محفوظة...`}
        style={{ marginBottom: 12 }}
      />
    );
  }

  return null;
};

export default OfflineBanner;
