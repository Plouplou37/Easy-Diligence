import { useNavigate } from 'react-router-dom';
import {
  ArrowPathIcon,
  ClipboardDocumentListIcon,
  MagnifyingGlassIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { Button, EmptyState, LoadingSpinner, PageHeader, pageLayout, panel } from '@/shared/ui';
import {
  DashboardTiles,
  SessionFilters,
  SessionsList,
  plural,
  useDashboard,
  useSessionFilters,
} from '@/widgets/sessions-overview';

/** The due diligences: what is running, what awaits review, which syntheses are ready. */
const Dashboard = () => {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const dashboard = useDashboard();
  const filters = useSessionFilters(dashboard.sessions);
  const { sessions } = dashboard;
  const shown = filters.filtered;

  if (dashboard.loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner size="lg" text="Loading due diligences…" />
      </div>
    );
  }

  const newDueDiligence = (
    <Button variant="primary" onClick={() => navigate('/session/create')} icon={PlusIcon}>
      New due diligence
    </Button>
  );

  return (
    <div className={pageLayout.container}>
      <PageHeader
        title="Due diligences"
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
            {newDueDiligence}
          </>
        }
      />

      <DashboardTiles
        totals={dashboard.totals}
        sessions={sessions}
        isLive={dashboard.isLive}
        filters={filters}
      />

      {sessions.length === 0 ? (
        <div className={panel.base}>
          <EmptyState
            icon={ClipboardDocumentListIcon}
            title="No due diligence yet"
            text="Create the first one: the fund, its documents and a questionnaire."
            action={newDueDiligence}
          />
        </div>
      ) : (
        <section aria-label="Due diligences" className={`${panel.base} overflow-hidden`}>
          <SessionFilters filters={filters} />
          {shown.length === 0 ? (
            <EmptyState
              icon={MagnifyingGlassIcon}
              title="No due diligence matches"
              text="Try another search, or clear the filters."
              action={
                <Button variant="secondary" onClick={filters.reset}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <SessionsList sessions={shown} showOwner={isAdmin} />
          )}
          <p className={`${panel.footer} text-xs text-content-muted tabular-nums`}>
            Showing {shown.length} of {plural(sessions.length, 'due diligence')}
          </p>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
