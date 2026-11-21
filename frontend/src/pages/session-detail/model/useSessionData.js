import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { fetchDdTypes } from '@/entities/dd-type';
import { sessionAPI } from '@/entities/session';

const POLL_MS = 3000;

/**
 * A session, the DD types, and the progress of the session's runs, polled
 * while one of them runs. `stale`: the poll stopped answering, so the figures
 * may be out of date. `loadProgress` reads the progress again (after a start,
 * a pause, a resume: a start re-arms the poll).
 */
export const useSessionData = sessionId => {
  const [session, setSession] = useState(null);
  const [ddTypes, setDdTypes] = useState([]);
  const [progressByCode, setProgressByCode] = useState({});
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);

  const loadProgress = useCallback(async () => {
    try {
      const response = await sessionAPI.getStatus(sessionId);
      setProgressByCode(Object.fromEntries(response.data.progress.map(run => [run.dd_type, run])));
      setStale(false);
    } catch {
      setStale(true);
    }
  }, [sessionId]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await sessionAPI.get(sessionId);
        setSession(response.data);
        // Inactive types too: a session built on a since-deactivated type still
        // shows it and its answers; starting it is refused instead.
        await Promise.allSettled([
          fetchDdTypes({ activeOnly: false }).then(setDdTypes),
          loadProgress(),
        ]);
      } catch {
        toast.error('Failed to load the due diligence');
        setSession(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [sessionId, loadProgress]);

  // Poll only while a run goes on.
  const isRunning = Object.values(progressByCode).some(run => run.status === 'in_progress');
  useEffect(() => {
    if (!isRunning) return undefined;
    const interval = setInterval(loadProgress, POLL_MS);
    return () => clearInterval(interval);
  }, [isRunning, loadProgress]);

  return { session, ddTypes, progressByCode, loading, stale, loadProgress };
};
