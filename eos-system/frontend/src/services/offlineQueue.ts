/**
 * EOS System — Offline Queue (P66)
 *
 * Guarantees for mobile field usage:
 * - A write (POST/PUT/DELETE) that fails due to lost connectivity is never
 *   dropped: it is persisted to localStorage and replayed automatically
 *   when the connection returns.
 * - UI hooks fire CustomEvents so any component can surface queue state.
 */

export interface QueuedRequest {
  id: string;
  url: string;
  method: 'post' | 'put' | 'delete';
  data?: unknown;
  createdAt: number;
  retries: number;
  description?: string;
}

const QUEUE_KEY = 'eos-offline-queue';
const MAX_QUEUE_SIZE = 200;

// Events consumed by OfflineBanner / pages
export const EV_QUEUE_CHANGED = 'eos-offline-queue-changed';
export const EV_SYNC_DONE = 'eos-offline-sync-done';

function readQueue(): QueuedRequest[] {
  try {
    const raw = localStorage.getItem(QUEUE_KEY);
    return raw ? (JSON.parse(raw) as QueuedRequest[]) : [];
  } catch {
    return [];
  }
}

function persistQueue(queue: QueuedRequest[]) {
  try {
    // Keep the newest MAX_QUEUE_SIZE operations
    const trimmed = queue.slice(-MAX_QUEUE_SIZE);
    localStorage.setItem(QUEUE_KEY, JSON.stringify(trimmed));
  } catch {
    // storage full — drop oldest half and retry once
    try {
      localStorage.setItem(QUEUE_KEY, JSON.stringify(queue.slice(-Math.floor(MAX_QUEUE_SIZE / 2))));
    } catch {
      /* give up silently; offline mode is best-effort */
    }
  }
}

function notifyChanged() {
  window.dispatchEvent(
    new CustomEvent(EV_QUEUE_CHANGED, { detail: { size: getQueueSize() } })
  );
}

/** Number of pending offline operations */
export function getQueueSize(): number {
  return readQueue().length;
}

/** Queue a failed write so it survives reloads / tunnel-outages */
export function enqueueQueuedRequest(req: Omit<QueuedRequest, 'id' | 'createdAt' | 'retries'>): void {
  const queue = readQueue();
  queue.push({
    ...req,
    id:
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    createdAt: Date.now(),
    retries: 0,
  });
  persistQueue(queue);
  notifyChanged();
}

/** Remove a successfully replayed operation */
function dequeue(id: string): void {
  persistQueue(readQueue().filter((q) => q.id !== id));
}

/**
 * Replay every queued request. Stops at the first persistent network failure
 * so ordering is preserved; client-side errors (4xx) are discarded because
 * retrying them will never succeed.
 */
export async function flushQueue(): Promise<{ synced: number; remaining: number }> {
  if (!navigator.onLine) return { synced: 0, remaining: getQueueSize() };

  // Lazy import avoids a hard module cycle at evaluation time
  const { default: apiClient } = await import('./apiClient');

  let synced = 0;
  const queue = readQueue();

  for (const item of queue) {
    try {
      await apiClient[item.method](item.url, item.data);
      dequeue(item.id);
      synced += 1;
      notifyChanged();
    } catch (err: any) {
      const networkFailure = !err?.response;
      if (networkFailure) break; // still offline → keep the rest queued, order intact
      // 4xx/5xx: business rejection — do not retry forever
      dequeue(item.id);
      notifyChanged();
    }
  }

  const remaining = getQueueSize();
  window.dispatchEvent(new CustomEvent(EV_SYNC_DONE, { detail: { synced, remaining } }));
  return { synced, remaining };
}

let initialized = false;

/** Wire global listeners once (called from main.tsx) */
export function initOfflineQueue(): void {
  if (initialized || typeof window === 'undefined') return;
  initialized = true;

  window.addEventListener('online', () => {
    void flushQueue();
  });

  // ServiceWorker background-sync nudge
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'REPLAY_OFFLINE_QUEUE') void flushQueue();
    });
  }

  notifyChanged();
}
