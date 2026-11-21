import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { getOverallStatus } from '@/entities/execution';
import { getSessionDdTypes } from '@/entities/session';
import { useDdRunControl } from '@/features/dd-run-control';
import { useVectorStoreAssignments } from '@/features/vector-store-assign';
import { Button, EmptyState, LoadingSpinner } from '@/shared/ui';
import { SessionWorkspace } from '@/widgets/session-workspace';
import { useSessionData } from '../model/useSessionData';

/**
 * A due diligence, as a workspace. The URL says what is shown:
 * `?dd_type=<code>` the questionnaire, `&tab=synthesis` its synthesis rather
 * than its questions (the old answers page redirects here with the same).
 */
const SessionDetail = () => {
  const { sessionId } = useParams(); // an id or a session code
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  // Read once: the URL changes below replace the history entry and its state.
  // The creation page says whether a document collection came with it.
  const [justCreated, setJustCreated] = useState(() => Boolean(location.state?.newSession));
  const [documentsAssigned] = useState(() => Boolean(location.state?.documentsAssigned));

  const { session, ddTypes, progressByCode, loading, stale, loadProgress } =
    useSessionData(sessionId);
  const stores = useVectorStoreAssignments({ sessionId, ddTypes });
  const runs = useDdRunControl({ sessionId, progressByCode, ddTypes, onChange: loadProgress });

  const loadStores = stores.load;
  useEffect(() => {
    loadStores();
  }, [loadStores]);

  const shownDdTypes = useMemo(
    () => getSessionDdTypes(session, ddTypes, progressByCode),
    [session, ddTypes, progressByCode]
  );
  const overall = useMemo(
    () => getOverallStatus(shownDdTypes, progressByCode),
    [shownDdTypes, progressByCode]
  );

  // The questionnaire asked for, else the one running, else the first.
  const requested = searchParams.get('dd_type');
  const selected =
    shownDdTypes.find(ddType => ddType.code === requested) ||
    shownDdTypes.find(ddType => progressByCode[ddType.code]?.status === 'in_progress') ||
    shownDdTypes[0] ||
    null;
  const tabParam = searchParams.get('tab');
  const tab = tabParam === 'synthesis' ? 'synthesis' : 'questions';

  const updateParams = useCallback(
    changes =>
      setSearchParams(
        previous => {
          const next = new URLSearchParams(previous);
          Object.entries(changes).forEach(([key, value]) =>
            value ? next.set(key, value) : next.delete(key)
          );
          return next;
        },
        { replace: true, preventScrollReset: true }
      ),
    [setSearchParams]
  );

  // The questionnaire chosen by default goes into the URL: it then stays put
  // when a run starts or ends, and the address can be shared as it is. The
  // old answers page's `tab=answers` is the questions, the default: dropped.
  const selectedCode = selected?.code;
  useEffect(() => {
    const changes = {};
    if (selectedCode && requested !== selectedCode) changes.dd_type = selectedCode;
    if (tabParam && tabParam !== 'synthesis') changes.tab = null;
    if (Object.keys(changes).length > 0) updateParams(changes);
  }, [selectedCode, requested, tabParam, updateParams]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="Loading the due diligence..." />
      </div>
    );
  }

  if (!session) {
    return (
      <EmptyState
        title="Due diligence not found"
        text="The requested due diligence could not be found, or you do not have access to it."
        action={
          <Button variant="secondary" onClick={() => navigate('/')}>
            Back to the due diligences
          </Button>
        }
      />
    );
  }

  return (
    <SessionWorkspace
      session={session}
      sessionId={sessionId}
      ddTypes={shownDdTypes}
      selected={selected}
      progressByCode={progressByCode}
      overall={overall}
      stale={stale}
      runs={runs}
      stores={stores}
      tab={tab}
      onTabChange={next => updateParams({ tab: next === 'synthesis' ? 'synthesis' : null })}
      onSelectDdType={code => updateParams({ dd_type: code })}
      justCreated={justCreated}
      documentsAssigned={documentsAssigned}
      onDismissCreated={() => setJustCreated(false)}
    />
  );
};

/** One page per session: opening another starts from a clean state. */
const SessionDetailPage = () => {
  const { sessionId } = useParams();
  return <SessionDetail key={sessionId} />;
};

export default SessionDetailPage;
