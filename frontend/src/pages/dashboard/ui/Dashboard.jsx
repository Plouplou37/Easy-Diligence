import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PlusIcon,
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  FunnelIcon,
  ChevronDownIcon,
  UsersIcon,
  UserIcon,
  ArrowPathIcon,
  PencilSquareIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { dashboardAPI } from '@/entities/session';
import { useAuth } from '@/entities/viewer';
import toast from 'react-hot-toast';
import { useDebounce, useLocalStorage } from '@/shared/lib/hooks';
import {
  Button,
  Card,
  Badge,
  EmptyState,
  LoadingSpinner,
  PageHeader,
  SearchInput,
  StatTile,
  StatusBadge,
  field,
  pageLayout,
  panel,
  tableStyles,
} from '@/shared/ui';
import { getToneStyles } from '@/shared/lib/status';
import {
  IN_PROGRESS_STATUSES,
  getSessionStatus,
  getSessionProgress,
} from '@/entities/execution';
import { SESSION_STATUS_OPTIONS } from '@/shared/lib/status';
import { getDdTypeIcon } from '@/entities/dd-type';

// Refreshed only while something moves (a run or a summary batch). The old page
// called /session/{id}/status for every session every 5 s, running or not.
const LIVE_REFRESH_MS = 15000;

// A run whose last answer is older than this is probably orphaned (server
// restarted mid-run): the execution stays `in_progress` with nothing behind it.
const STALLED_AFTER_MS = 10 * 60 * 1000;

const formatRelative = (iso) => {
  if (!iso) return '—';
  const date = new Date(iso);
  const minutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} d ago`;
  return date.toLocaleDateString();
};

const ProgressBar = ({ percentage }) => {
  const fill = getToneStyles(percentage >= 100 ? 'success' : percentage > 0 ? 'info' : 'neutral').fill;
  return (
    <div className="flex-1 h-1.5 rounded-full bg-surface-hover overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-300 ${fill}`} style={{ width: `${percentage}%` }} />
    </div>
  );
};

const Dashboard = () => {
  const [data, setData] = useState({ sessions: [], totals: {} });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { isAdmin } = useAuth();
  const navigate = useNavigate();

  // Search and filter states with localStorage persistence
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useLocalStorage('dashboard-statusFilter', 'all');
  const [dateFilter, setDateFilter] = useLocalStorage('dashboard-dateFilter', 'all');
  const [sortBy, setSortBy] = useLocalStorage('dashboard-sortBy', 'activity');
  const [reviewOnly, setReviewOnly] = useLocalStorage('dashboard-reviewOnly', false);
  const [showFilters, setShowFilters] = useState(false);
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const loadData = useCallback(async ({ silent = false } = {}) => {
    try {
      const response = await dashboardAPI.sessions();
      setData(response.data || { sessions: [], totals: {} });
    } catch (error) {
      if (!silent) toast.error('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const sessions = useMemo(() => (data.sessions || []).map((session) => ({
    ...session,
    status: getSessionStatus(session.dd_types, session.dd_types.length),
    progress: getSessionProgress(session.dd_types, session.dd_types.length),
    toReview: session.dd_types.reduce((sum, d) => sum + (d.to_review || 0), 0),
  })), [data]);

  const isLive = sessions.some(
    (s) => s.batch_pending || s.dd_types.some((d) => d.status === 'in_progress')
  );

  useEffect(() => {
    if (!isLive) return undefined;
    const interval = setInterval(() => loadData({ silent: true }), LIVE_REFRESH_MS);
    return () => clearInterval(interval);
  }, [isLive, loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const filteredSessions = useMemo(() => {
    let filtered = [...sessions];

    if (debouncedSearchTerm) {
      const term = debouncedSearchTerm.toLowerCase();
      filtered = filtered.filter((s) =>
        s.name?.toLowerCase().includes(term) ||
        s.description?.toLowerCase().includes(term) ||
        s.company_name?.toLowerCase().includes(term) ||
        s.management_company_name?.toLowerCase().includes(term) ||
        s.dd_types.some((d) => d.name?.toLowerCase().includes(term))
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter((s) => s.status === statusFilter);
    }

    if (reviewOnly) {
      filtered = filtered.filter((s) => s.toReview > 0);
    }

    if (dateFilter !== 'all') {
      const filterDate = new Date();
      if (dateFilter === 'today') filterDate.setHours(0, 0, 0, 0);
      if (dateFilter === 'week') filterDate.setDate(filterDate.getDate() - 7);
      if (dateFilter === 'month') filterDate.setMonth(filterDate.getMonth() - 1);
      filtered = filtered.filter((s) => new Date(s.created_at) >= filterDate);
    }

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'recent':
          return new Date(b.created_at) - new Date(a.created_at);
        case 'oldest':
          return new Date(a.created_at) - new Date(b.created_at);
        case 'name':
          return a.name.localeCompare(b.name);
        case 'progress':
          return b.progress - a.progress;
        case 'review':
          return b.toReview - a.toReview;
        case 'activity':
        default:
          return new Date(b.last_activity_at) - new Date(a.last_activity_at);
      }
    });

    return filtered;
  }, [sessions, debouncedSearchTerm, statusFilter, reviewOnly, dateFilter, sortBy]);

  // Per-user counts of the admin table, from the same data.
  const userStatistics = useMemo(() => {
    if (!isAdmin) return {};
    const byUser = {};
    sessions.forEach((session) => {
      const userId = session.created_by || session.assigned_to;
      if (!userId) return;
      if (!byUser[userId]) {
        byUser[userId] = {
          username: session.created_by_username || `User ${userId}`,
          totalSessions: 0,
          completedSessions: 0,
          inProgressSessions: 0,
          toReview: 0,
        };
      }
      const stats = byUser[userId];
      stats.totalSessions++;
      stats.toReview += session.toReview;
      if (session.status === 'completed') stats.completedSessions++;
      else if (IN_PROGRESS_STATUSES.includes(session.status)) stats.inProgressSessions++;
    });
    return byUser;
  }, [sessions, isAdmin]);

  if (loading) {
    return (
      <>
        <div className="flex items-center justify-center min-h-[60vh]">
          <LoadingSpinner size="lg" text="Loading dashboard..." />
        </div>
      </>
    );
  }

  const totals = data.totals || {};
  const filtersActive = debouncedSearchTerm || statusFilter !== 'all' || dateFilter !== 'all' || reviewOnly;
  const openSession = (session) => navigate(`/session/${session.session_code || session.id}`);
  const openAnswers = (session, ddType, tab) =>
    navigate(`/session/${session.session_code || session.id}/answers?dd_type=${ddType.code}${tab ? `&tab=${tab}` : ''}`);

  return (
    <>
      <div className={pageLayout.container}>
        <PageHeader
          title="Due Diligence Dashboard"
          subtitle="What is running, what awaits review, and which syntheses are ready"
          actions={(
            <>
              <Button variant="secondary" onClick={handleRefresh} loading={refreshing} icon={ArrowPathIcon}>
                Refresh
              </Button>
              <Button variant="primary" onClick={() => navigate('/session/create')} icon={PlusIcon}>
                New Session
              </Button>
            </>
          )}
        />

        {/* Tiles centred on what calls for an action; the first two filter the table. */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Answers to review"
            value={totals.to_review || 0}
            hint={reviewOnly ? 'Showing sessions with answers to review' : 'Not approved yet'}
            icon={PencilSquareIcon}
            iconClass="text-theme-warning"
            onClick={() => setReviewOnly(!reviewOnly)}
            active={reviewOnly}
          />
          <StatTile
            label="Running"
            value={totals.running || 0}
            hint={isLive ? 'Refreshing every 15 s' : 'Nothing running'}
            icon={ClockIcon}
            iconClass="text-accent-blue"
            onClick={() => setStatusFilter(statusFilter === 'in_progress' ? 'all' : 'in_progress')}
            active={statusFilter === 'in_progress'}
          />
          <StatTile
            label="Syntheses ready"
            value={totals.syntheses_ready || 0}
            icon={SparklesIcon}
            iconClass="text-accent-gold"
          />
          <StatTile
            label="Sessions"
            value={totals.sessions || 0}
            hint={`${sessions.filter((s) => s.status === 'completed').length} completed`}
            icon={DocumentTextIcon}
          />
        </div>

        {/* Search and Filters */}
        <div className={`${panel.base} p-5`}>
          <div className="flex flex-col sm:flex-row gap-3">
            <SearchInput
              className="flex-1"
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Search sessions by name, fund, management company or DD type..."
            />
            <Button variant="secondary" onClick={() => setShowFilters(!showFilters)} icon={FunnelIcon}>
              Filters
              <ChevronDownIcon className={`w-4 h-4 transform transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </Button>
          </div>

          {showFilters && (
            <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 gap-4 sm:grid-cols-4">
              <div>
                <label htmlFor="status-filter" className={field.label}>Status</label>
                <select
                  id="status-filter"
                  className={`${field.input} py-2 text-sm`}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All Statuses</option>
                  {SESSION_STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="date-filter" className={field.label}>Created</label>
                <select
                  id="date-filter"
                  className={`${field.input} py-2 text-sm`}
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                >
                  <option value="all">All Time</option>
                  <option value="today">Today</option>
                  <option value="week">Last 7 Days</option>
                  <option value="month">Last 30 Days</option>
                </select>
              </div>
              <div>
                <label htmlFor="sort-by" className={field.label}>Sort By</label>
                <select
                  id="sort-by"
                  className={`${field.input} py-2 text-sm`}
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                >
                  <option value="activity">Latest Activity</option>
                  <option value="review">Most to Review</option>
                  <option value="recent">Newest First</option>
                  <option value="oldest">Oldest First</option>
                  <option value="name">Name (A-Z)</option>
                  <option value="progress">Progress (%)</option>
                </select>
              </div>
              <label className="flex items-end gap-2 pb-2 text-sm text-content cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded"
                  checked={reviewOnly}
                  onChange={(e) => setReviewOnly(e.target.checked)}
                />
                With answers to review
              </label>
            </div>
          )}
        </div>

        {/* Sessions, one sub-row per DD type */}
        {filteredSessions.length === 0 ? (
          <div className={panel.base}>
            <EmptyState
              icon={DocumentTextIcon}
              title="No sessions found"
              text={filtersActive ? 'Try adjusting your filters' : 'Get started by creating a new due diligence session.'}
              action={!filtersActive && (
                <Button variant="primary" onClick={() => navigate('/session/create')} icon={PlusIcon}>
                  New Session
                </Button>
              )}
            />
          </div>
        ) : (
          <div className={`${panel.base} overflow-hidden`}>
            <div className={tableStyles.wrapper}>
              <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
                <thead className={tableStyles.thead}>
                  <tr>
                    <th className={tableStyles.th}>Session</th>
                    <th className={tableStyles.th}>Fund / Management Company</th>
                    <th className={tableStyles.th}>Status</th>
                    <th className={tableStyles.th}>Last Activity</th>
                    <th className={`${tableStyles.th} w-48`}>Progress</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSessions.map((session) => (
                    <React.Fragment key={session.id}>
                      <tr onClick={() => openSession(session)} className={`${tableStyles.row} cursor-pointer`}>
                        <td className={tableStyles.td}>
                          <span className="block max-w-md text-sm font-medium text-content truncate" title={session.description || session.name}>
                            {session.name}
                          </span>
                          {isAdmin && session.created_by_username && (
                            <span className="text-xs text-content-muted">{session.created_by_username}</span>
                          )}
                        </td>
                        <td className={`${tableStyles.td} text-sm`}>
                          <span className="block">{session.company_name}</span>
                          {session.management_company_name && (
                            <span className="block text-xs text-content-secondary">{session.management_company_name}</span>
                          )}
                        </td>
                        <td className={tableStyles.td}>
                          <StatusBadge status={session.status} />
                        </td>
                        <td
                          className={`${tableStyles.td} whitespace-nowrap text-content-secondary tabular-nums`}
                          title={`Created ${new Date(session.created_at).toLocaleDateString()}`}
                        >
                          {formatRelative(session.last_activity_at)}
                        </td>
                        <td className={tableStyles.td}>
                          <div className="flex items-center gap-2">
                            <ProgressBar percentage={session.progress} />
                            <span className="w-9 text-right text-xs font-medium text-content tabular-nums">
                              {session.progress}%
                            </span>
                          </div>
                        </td>
                      </tr>

                      {session.dd_types.map((ddType) => {
                        const Icon = getDdTypeIcon(ddType);
                        const started = ddType.status !== 'not_started';
                        const stalled = ddType.status === 'in_progress' && ddType.last_answer_at &&
                          Date.now() - new Date(ddType.last_answer_at).getTime() > STALLED_AFTER_MS;
                        return (
                          <tr key={`${session.id}-${ddType.dd_type_id}`} className="bg-surface-bg">
                            <td className={`${tableStyles.td} pl-8`}>
                              <span className="flex items-center gap-2 min-w-0">
                                <Icon className="w-4 h-4 flex-shrink-0 text-content-muted" />
                                <span className="truncate text-content-secondary" title={ddType.name}>{ddType.name}</span>
                                {ddType.is_active === false && <Badge variant="warning" size="sm">Inactive</Badge>}
                              </span>
                            </td>
                            <td className={tableStyles.td}>
                              <span className="flex flex-wrap items-center gap-2">
                                {ddType.to_review > 0 && (
                                  <Badge variant="warning" size="sm" icon={PencilSquareIcon}>
                                    {ddType.to_review} to review
                                  </Badge>
                                )}
                                {ddType.failed > 0 && (
                                  <Badge variant="error" size="sm">{ddType.failed} failed</Badge>
                                )}
                                {ddType.has_synthesis && (
                                  <Badge variant="success" size="sm" icon={CheckCircleIcon}>Synthesis</Badge>
                                )}
                              </span>
                            </td>
                            <td className={tableStyles.td}>
                              <span className="flex items-center gap-1.5">
                                <StatusBadge status={ddType.status} size="sm" />
                                {stalled && (
                                  <span title={`No new answer since ${new Date(ddType.last_answer_at).toLocaleString()}: the run may have stopped. Open the session to resume it.`}>
                                    <ExclamationTriangleIcon className="w-4 h-4 text-theme-warning" />
                                  </span>
                                )}
                              </span>
                            </td>
                            <td className={`${tableStyles.td} whitespace-nowrap`}>
                              {started ? (
                                <span className="flex items-center gap-1">
                                  <Button size="sm" variant="secondary" onClick={() => openAnswers(session, ddType)}>
                                    Answers
                                  </Button>
                                  {ddType.has_synthesis && (
                                    <Button size="sm" variant="ghost" onClick={() => openAnswers(session, ddType, 'synthesis')}>
                                      Synthesis
                                    </Button>
                                  )}
                                </span>
                              ) : (
                                <Button size="sm" variant="ghost" onClick={() => openSession(session)}>
                                  Open
                                </Button>
                              )}
                            </td>
                            <td className={tableStyles.td}>
                              <div className="flex items-center gap-2">
                                <ProgressBar percentage={ddType.percentage} />
                                <span className="w-14 text-right text-xs text-content-secondary tabular-nums">
                                  {ddType.answered}/{ddType.total_questions}
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {filteredSessions.length > 0 && (
          <div className="text-xs text-content-muted text-center">
            Showing {filteredSessions.length} of {sessions.length} sessions
          </div>
        )}

        {/* Admin User Statistics */}
        {isAdmin && Object.keys(userStatistics).length > 0 && (
          <Card
            title={(
              <>
                <UsersIcon className="h-4 w-4 text-content-muted" />
                User Analytics
              </>
            )}
            noPadding
          >
            <div className={tableStyles.wrapper}>
              <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
                <thead className={tableStyles.thead}>
                  <tr>
                    <th className={tableStyles.th}>User</th>
                    <th className={tableStyles.thCenter}>Sessions</th>
                    <th className={tableStyles.thCenter}>Completed</th>
                    <th className={tableStyles.thCenter}>In Progress</th>
                    <th className={tableStyles.thCenter}>Answers to Review</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(userStatistics).map(([userId, stats], index) => (
                    <tr key={userId} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
                      <td className={tableStyles.td}>
                        <div className="flex items-center gap-2">
                          <UserIcon className="h-4 w-4 text-content-muted" />
                          <span className="text-sm font-medium">{stats.username}</span>
                        </div>
                      </td>
                      <td className={`${tableStyles.tdCenter} tabular-nums`}>{stats.totalSessions}</td>
                      <td className={tableStyles.tdCenter}>
                        <Badge variant="success">{stats.completedSessions}</Badge>
                      </td>
                      <td className={tableStyles.tdCenter}>
                        <Badge variant="info">{stats.inProgressSessions}</Badge>
                      </td>
                      <td className={`${tableStyles.tdCenter} tabular-nums`}>{stats.toReview}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </>
  );
};

export default Dashboard;
