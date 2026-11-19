import { useNavigate } from 'react-router-dom';
import { ArrowPathIcon, DocumentTextIcon, PlusIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { Button, EmptyState, LoadingSpinner, PageHeader, pageLayout, panel } from '@/shared/ui';
import {
  DashboardTiles,
  SessionFilters,
  SessionsTable,
  UserStatsTable,
  useDashboard,
  useSessionFilters,
} from '@/widgets/sessions-overview';

const Dashboard = () => {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const dashboard = useDashboard();
  const filters = useSessionFilters(dashboard.sessions);
  const { sessions } = dashboard;
  const shown = filters.filtered;

  if (dashboard.loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text="Loading dashboard..." />
      </div>
    );
  }

  const newSession = (
    <Button variant="primary" onClick={() => navigate('/session/create')} icon={PlusIcon}>
      New Session
    </Button>
  );

  return (
    <div className={pageLayout.container}>
      <PageHeader
        title="Due Diligence Dashboard"
        subtitle="What is running, what awaits review, and which syntheses are ready"
        actions={
          <>
            <Button
              variant="secondary"
              onClick={dashboard.refresh}
              loading={dashboard.refreshing}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
            {newSession}
          </>
        }
      />

      <DashboardTiles
        totals={dashboard.totals}
        sessions={sessions}
        isLive={dashboard.isLive}
        filters={filters}
      />
      <SessionFilters filters={filters} />

      {shown.length === 0 ? (
        <div className={panel.base}>
          <EmptyState
            icon={DocumentTextIcon}
            title="No sessions found"
            text={
              filters.active
                ? 'Try adjusting your filters'
                : 'Get started by creating a new due diligence session.'
            }
            action={!filters.active && newSession}
          />
        </div>
      ) : (
        <>
          <div className={`${panel.base} overflow-hidden`}>
            <SessionsTable sessions={shown} showOwner={isAdmin} />
          </div>
          <div className="text-xs text-content-muted text-center">
            Showing {shown.length} of {sessions.length} sessions
          </div>
        </>
      )}

      {isAdmin && <UserStatsTable sessions={sessions} />}
    </div>
  );
};

export default Dashboard;
