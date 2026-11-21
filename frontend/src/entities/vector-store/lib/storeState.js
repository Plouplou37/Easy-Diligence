// The statuses of a store gone at OpenAI (STALE in services/vector_stores.py).
// Its documents are gone with it; the page's Refresh removes such stores.
const STALE_STATUSES = ['expired', 'missing'];

const DAY_MS = 24 * 60 * 60 * 1000;

/** Whether the store is gone at OpenAI: it can no longer be searched. */
export const isStale = store => STALE_STATUSES.includes(store?.status);

/**
 * Whether the store's figures are unknown: OpenAI could not describe it (out
 * of reach, key refused…). The backend says why in `problem`.
 */
export const isUnknown = store => store?.status === 'error';

/** The store's state, for its badge: a label and a tone, or null when usable. */
export const storeState = store => {
  if (store?.status === 'expired') return { label: 'Expired', tone: 'error' };
  if (store?.status === 'missing') return { label: 'Gone', tone: 'error' };
  if (isUnknown(store)) return { label: 'Unknown', tone: 'warning' };
  return null;
};

/** What the state of a store means for its user, or null when it is usable. */
export const storeProblem = store => {
  if (store?.status === 'expired') {
    return 'This vector store expired at OpenAI after going unused: its documents are gone, and the DD runs it is assigned to can no longer search them.';
  }
  if (store?.status === 'missing') {
    return 'This vector store no longer exists at OpenAI: its documents are gone, and the DD runs it is assigned to can no longer search them.';
  }
  if (isUnknown(store)) {
    return `${store.problem || 'OpenAI did not describe this vector store.'} Its figures are unknown for now.`;
  }
  return null;
};

/** How close a usable store is to expiring: 'soon' (a week), 'imminent' (3 days) or null. */
export const expiryLevel = store => {
  if (!store?.expires_at || isStale(store)) return null;
  const days = (new Date(store.expires_at) - Date.now()) / DAY_MS;
  if (days <= 3) return 'imminent';
  if (days <= 7) return 'soon';
  return null;
};
