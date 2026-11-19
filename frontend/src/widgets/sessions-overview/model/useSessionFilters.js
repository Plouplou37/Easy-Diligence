import { useMemo, useState } from 'react';
import { useDebounce, useLocalStorage } from '@/shared/lib/hooks';

const since = (period) => {
  const date = new Date();
  if (period === 'today') date.setHours(0, 0, 0, 0);
  if (period === 'week') date.setDate(date.getDate() - 7);
  if (period === 'month') date.setMonth(date.getMonth() - 1);
  return date;
};

const COMPARE = {
  recent: (a, b) => new Date(b.created_at) - new Date(a.created_at),
  oldest: (a, b) => new Date(a.created_at) - new Date(b.created_at),
  name: (a, b) => a.name.localeCompare(b.name),
  progress: (a, b) => b.progress - a.progress,
  review: (a, b) => b.toReview - a.toReview,
  activity: (a, b) => new Date(b.last_activity_at) - new Date(a.last_activity_at),
};

/**
 * Search, filters and sort of the dashboard's sessions. The filters and the
 * sort are remembered in the browser; the search is not.
 */
export const useSessionFilters = (sessions) => {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useLocalStorage('dashboard-statusFilter', 'all');
  const [period, setPeriod] = useLocalStorage('dashboard-dateFilter', 'all');
  const [sortBy, setSortBy] = useLocalStorage('dashboard-sortBy', 'activity');
  const [reviewOnly, setReviewOnly] = useLocalStorage('dashboard-reviewOnly', false);
  const term = useDebounce(search, 300).toLowerCase();

  const filtered = useMemo(() => {
    const matches = (session) =>
      !term ||
      [session.name, session.description, session.company_name, session.management_company_name]
        .some((text) => text?.toLowerCase().includes(term)) ||
      session.dd_types.some((ddType) => ddType.name?.toLowerCase().includes(term));
    const from = period === 'all' ? null : since(period);
    return sessions
      .filter(matches)
      .filter((session) => status === 'all' || session.status === status)
      .filter((session) => !reviewOnly || session.toReview > 0)
      .filter((session) => !from || new Date(session.created_at) >= from)
      .sort(COMPARE[sortBy] || COMPARE.activity);
  }, [sessions, term, status, reviewOnly, period, sortBy]);

  return {
    search,
    setSearch,
    status,
    setStatus,
    period,
    setPeriod,
    sortBy,
    setSortBy,
    reviewOnly,
    setReviewOnly,
    filtered,
    active: Boolean(term) || status !== 'all' || period !== 'all' || reviewOnly,
  };
};
