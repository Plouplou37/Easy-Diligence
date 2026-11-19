import { useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { getSessionProgress, getSessionStatus } from '@/entities/execution';
import { dashboardAPI } from '@/entities/session';

// Refreshed only while something moves (a run or a summary batch). The old page
// called /session/{id}/status for every session every 5 s, running or not.
export const LIVE_REFRESH_MS = 15000;

/**
 * The dashboard's data, in one request (GET /dashboard/sessions): every
 * session with its DD types, and the totals. Each session gains its overall
 * status, progress and count of answers to review.
 */
export const useDashboard = () => {
  const [data, setData] = useState({ sessions: [], totals: {} });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async ({ silent = false } = {}) => {
    try {
      const response = await dashboardAPI.sessions();
      setData(response.data || { sessions: [], totals: {} });
    } catch {
      if (!silent) toast.error('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const sessions = useMemo(
    () =>
      (data.sessions || []).map((session) => ({
        ...session,
        status: getSessionStatus(session.dd_types, session.dd_types.length),
        progress: getSessionProgress(session.dd_types, session.dd_types.length),
        toReview: session.dd_types.reduce((sum, ddType) => sum + (ddType.to_review || 0), 0),
      })),
    [data]
  );

  const isLive = sessions.some(
    (session) => session.batch_pending || session.dd_types.some((ddType) => ddType.status === 'in_progress')
  );

  useEffect(() => {
    if (!isLive) return undefined;
    const interval = setInterval(() => load({ silent: true }), LIVE_REFRESH_MS);
    return () => clearInterval(interval);
  }, [isLive, load]);

  const refresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return { sessions, totals: data.totals || {}, loading, refreshing, refresh, isLive };
};
