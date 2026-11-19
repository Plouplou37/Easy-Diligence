import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { CheckCircleIcon, ClockIcon } from '@heroicons/react/24/outline';
import { fetchDdTypes } from '@/entities/dd-type';
import { FINISHED_STATUSES, getOverallStatus } from '@/entities/execution';
import { getSessionDdTypes, sessionAPI } from '@/entities/session';
import { useDdRunControl } from '@/features/dd-run-control';
import { DeleteSessionButton, ExportPdfButton } from '@/features/session-actions';
import { AssignAllSelect, useVectorStoreAssignments } from '@/features/vector-store-assign';
import {
  Button,
  EmptyState,
  LoadingSpinner,
  PageHeader,
  pageLayout,
  sectionHeader,
} from '@/shared/ui';
import { DDCard } from '@/widgets/dd-run-card';
import { SessionProgressPanel } from '@/widgets/session-progress';

const POLL_MS = 3000;

const SessionDetail = () => {
  const { sessionId } = useParams(); // an id or a session code
  const navigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = useState(null);
  const [progressByCode, setProgressByCode] = useState({});
  const [ddTypes, setDdTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  // The poll is the only thing that moves this page while a DD runs: when it
  // stops answering, say so rather than look stalled.
  const [progressStale, setProgressStale] = useState(false);

  const loadProgress = useCallback(async () => {
    try {
      const response = await sessionAPI.getStatus(sessionId);
      setProgressByCode(Object.fromEntries(response.data.progress.map(run => [run.dd_type, run])));
      setProgressStale(false);
    } catch {
      setProgressStale(true);
    }
  }, [sessionId]);

  const stores = useVectorStoreAssignments({ sessionId, ddTypes });
  const runs = useDdRunControl({ sessionId, progressByCode, ddTypes, onChange: loadProgress });
  const loadStores = stores.load;

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await sessionAPI.get(sessionId);
        setSession(response.data);
        // Inactive types too: a session built on a since-deactivated type still
        // shows its card and its answers; starting it is refused instead.
        await Promise.allSettled([
          fetchDdTypes({ activeOnly: false }).then(setDdTypes),
          loadProgress(),
          loadStores(),
        ]);
      } catch {
        toast.error('Failed to load session data');
        setSession(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [sessionId, loadProgress, loadStores]);

  // Poll only while a DD runs; Start and Resume reload the progress, which re-arms it.
  useEffect(() => {
    if (!runs.isRunning) return undefined;
    const interval = setInterval(loadProgress, POLL_MS);
    return () => clearInterval(interval);
  }, [runs.isRunning, loadProgress]);

  const shownDdTypes = useMemo(
    () => getSessionDdTypes(session, ddTypes, progressByCode),
    [session, ddTypes, progressByCode]
  );
  const overall = useMemo(
    () => getOverallStatus(shownDdTypes, progressByCode),
    [shownDdTypes, progressByCode]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="Loading session details..." />
      </div>
    );
  }

  if (!session) {
    return (
      <EmptyState
        title="Session not found"
        text="The requested session could not be found, or you do not have access to it."
        action={
          <Button variant="secondary" onClick={() => navigate('/')}>
            Back to Dashboard
          </Button>
        }
      />
    );
  }

  const answersUrl = (code, extra = '') => `/session/${sessionId}/answers?dd_type=${code}${extra}`;
  const anyFinished = Object.values(progressByCode).some(run =>
    FINISHED_STATUSES.includes(run.status)
  );

  return (
    <div className={pageLayout.container}>
      <PageHeader
        breadcrumb={[{ label: session.name || 'Session' }]}
        title={session.name}
        subtitle={session.description}
        meta={
          <span
            className="tabular-nums"
            title={`Session code: ${session.session_code || `SES-${session.id}`}`}
          >
            Created {new Date(session.created_at).toLocaleDateString()}
            {session.company_name && ` · ${session.company_name}`}
            {session.management_company_name && ` · ${session.management_company_name}`}
          </span>
        }
        actions={
          <>
            {anyFinished && <ExportPdfButton sessionId={sessionId} />}
            <DeleteSessionButton session={session} sessionId={sessionId} />
          </>
        }
      />

      {location.state?.newSession && (
        <div className="alert alert-success">
          <div className="flex items-start space-x-3">
            <CheckCircleIcon className="w-5 h-5 mt-0.5 flex-shrink-0 text-theme-success" />
            <div>
              <h3 className="text-sm font-medium text-theme-success">Session created</h3>
              <p className="text-sm text-content-secondary mt-1">
                Your due diligence session is ready. Next step: Create and assign document
                collections below to enable AI-powered analysis.
              </p>
            </div>
          </div>
        </div>
      )}

      <SessionProgressPanel overall={overall} isRunning={runs.isRunning} stale={progressStale} />

      <div>
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex-1 min-w-0">
            <div className={sectionHeader.wrapper}>
              <h2 className={sectionHeader.title}>Due Diligence Analysis</h2>
              <div className={sectionHeader.hairline} />
            </div>
            <span className="mt-1 block text-sm text-content-muted">
              {shownDdTypes.length} type{shownDdTypes.length !== 1 ? 's' : ''} configured
            </span>
          </div>
          <AssignAllSelect
            vectorStores={stores.vectorStores}
            onAssign={storeId =>
              stores.assignAll(
                storeId,
                shownDdTypes.map(ddType => ddType.code)
              )
            }
          />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {shownDdTypes.map(ddType => {
            const progress = progressByCode[ddType.code];
            const canStart = runs.canStart(ddType);
            return (
              <div key={ddType.code} className="relative">
                <DDCard
                  ddType={ddType}
                  progress={progress}
                  onStart={canStart ? runs.start : null}
                  onResume={runs.resume}
                  onPause={runs.pause}
                  onView={code => navigate(answersUrl(code))}
                  onSynthesis={code => navigate(answersUrl(code, '&tab=synthesis'))}
                  disabled={!canStart && progress?.status !== 'in_progress'}
                  vectorStores={stores.vectorStores}
                  assignedVectorStore={stores.assignedTo(ddType.code)}
                  onAssignVectorStore={stores.assign}
                  onRemoveVectorStore={stores.remove}
                />
                {!canStart && progress?.status === 'not_started' && (
                  <div className="absolute inset-0 bg-surface-bg/75 rounded-lg flex items-center justify-center">
                    <div className="text-center p-4">
                      <ClockIcon className="w-8 h-8 text-content-muted mx-auto mb-2" />
                      <p className="text-sm text-content-secondary">
                        Wait for other DD to complete
                      </p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SessionDetail;
