import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  CheckCircleIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  ExclamationTriangleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import Layout from '../components/Layout';
import DDCard from '../components/DDCard';
import {
  Button,
  EmptyState,
  LoadingSpinner,
  PageHeader,
  StatusBadge,
  pageLayout,
  panel,
  sectionHeader,
} from '../components/ui';
import { FINISHED_STATUSES, getSessionStatus } from '../utils/executionStatus';
import { sessionAPI, processingAPI, ddTypesAPI, vectorStoresAPI, answersAPI } from '../services/api';
import { downloadBlob } from '../features/answers/utils/exportHelpers';
import toast from 'react-hot-toast';

const SessionDetail = () => {
  const { sessionId: sessionIdentifier } = useParams();  // Can be either ID or session_code
  const navigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = useState(null);
  const [sessionProgress, setSessionProgress] = useState({});
  const [ddTypes, setDdTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [vectorStores, setVectorStores] = useState([]);
  const [vectorStoreAssignments, setVectorStoreAssignments] = useState({});
  // An assignment with no DD type covers every type of the session -- see
  // get_vector_store_ids_for_processing. Kept apart from the per-type map
  // because that map is keyed by DD type code, which such an assignment has
  // none of, and because the DD types load in parallel with the assignments.
  const [sessionWideVectorStore, setSessionWideVectorStore] = useState(null);
  const [bulkAssignValue, setBulkAssignValue] = useState('');
  // The 3s poll is the only thing that moves this page while a DD runs; when it
  // stops answering the numbers freeze, so say so rather than look stalled.
  const [progressStale, setProgressStale] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Computed values that depend on state - must be declared after all useState hooks
  const relevantDdTypes = useMemo(() => getSessionDdTypes(), [session, ddTypes, sessionProgress]);
  const overallStatus = useMemo(() => getOverallStatus(relevantDdTypes), [relevantDdTypes, sessionProgress]);

  // No safety timeout here any more. loadSessionData clears `loading` in a
  // finally block, so it could only fire spuriously: the effect depends on
  // [sessionIdentifier], so its `loading` was captured as true at the first
  // render and the condition was always satisfied. On a slow backend it
  // dropped the page into "Session not found" while the request was still
  // in flight.
  useEffect(() => {
    if (sessionIdentifier) {
      loadSessionData();
    }
  }, [sessionIdentifier]);

  // Poll only while a DD runs: the 3 s loop used to run for as long as the page
  // stayed open. Start / Resume reload the progress, which re-arms it.
  const isRunning = Object.values(sessionProgress).some(p => p.status === 'in_progress');
  useEffect(() => {
    if (!sessionIdentifier || !isRunning) return undefined;
    const interval = setInterval(loadSessionProgress, 3000);
    return () => clearInterval(interval);
  }, [sessionIdentifier, isRunning]);

  const loadSessionData = async () => {
    try {
      setLoading(true);

      // Load session first
      const sessionData = await loadSession();

      // Only load other data if session loaded successfully
      if (sessionData) {
        // Load data in parallel but handle each error individually
        await Promise.allSettled([
          loadDdTypes(),
          loadSessionProgress(),
          loadVectorStores(),
          loadVectorStoreAssignments()
        ]);
      }
    } catch (error) {
      console.error('Error loading session data:', error);
      toast.error('Failed to load session data');
      setSession(null); // Ensure session is null on error
    } finally {
      // Always clear loading state, even if there are errors
      setLoading(false);
    }
  };

  const loadSession = async () => {
    try {
      const response = await sessionAPI.get(sessionIdentifier);
      setSession(response.data);
      return response.data;
    } catch (error) {
      throw error;
    }
  };

  const loadDdTypes = async () => {
    // Include inactive types. Deactivating a type means "no longer offered when
    // creating a session", not "the work already done on it disappears": a
    // session built on a since-deactivated type still has to show its card and
    // its answers. Starting one is blocked in canStartDD instead.
    const response = await ddTypesAPI.list(false);
    setDdTypes(response.data);
  };

  const loadSessionProgress = async () => {
    if (!sessionIdentifier) return;

    try {
      const response = await sessionAPI.getStatus(sessionIdentifier);
      const progressData = {};
      response.data.progress.forEach(p => {
        progressData[p.dd_type] = p;
      });
      setSessionProgress(progressData);
      setProgressStale(false);
    } catch (error) {
      // Polled every 3s: a failing backend used to leave the progress frozen
      // with nothing on screen to distinguish it from a stalled run.
      setProgressStale(true);
    }
  };

  const canStartDD = (ddType) => {
    // A deactivated type stays visible so its existing answers remain readable,
    // but it must not be runnable any more -- that is what deactivating it means.
    if (ddType.is_active === false) {
      return false;
    }

    // Check if any other DD is currently running
    const hasRunningDD = Object.values(sessionProgress).some(
      progress => progress.status === 'in_progress'
    );

    if (hasRunningDD) {
      return false; // Can't start if another DD is running
    }

    const currentProgress = sessionProgress[ddType.code];
    return !currentProgress || ['not_started', 'failed', 'paused'].includes(currentProgress.status);
  };

  // Toasts name the DD type, not its internal code.
  const ddTypeName = (code) => ddTypes.find(dd => dd.code === code)?.name || code;

  const handleStartDD = async (ddType) => {
    try {
      await processingAPI.start(sessionIdentifier, ddType);
      toast.success(`Started ${ddTypeName(ddType)}`);
      await loadSessionProgress();
    } catch (error) {
      toast.error('Failed to start DD processing');
    }
  };

  const handleResumeDD = async (ddType) => {
    try {
      await processingAPI.resume(sessionIdentifier, ddType);
      toast.success(`Resumed ${ddTypeName(ddType)}`);
      await loadSessionProgress();
    } catch (error) {
      toast.error('Failed to resume DD processing');
    }
  };

  const handlePauseDD = async (ddType) => {
    try {
      await processingAPI.pause(sessionIdentifier, ddType);
      toast.success(`Paused ${ddTypeName(ddType)}`);
      await loadSessionProgress();
    } catch (error) {
      toast.error('Failed to pause DD processing');
    }
  };

  const handleViewDD = (ddType) => {
    navigate(`/session/${sessionIdentifier}/answers?dd_type=${ddType}`);
  };

  const handleSynthesisDD = (ddType) => {
    navigate(`/session/${sessionIdentifier}/answers?dd_type=${ddType}&tab=synthesis`);
  };

  // The PDF covers the whole session (synthesis per DD type + annexes).
  const handleExportPdf = async () => {
    setExporting(true);
    try {
      const res = await answersAPI.export(sessionIdentifier);
      downloadBlob(res.data, `session-${sessionIdentifier}-DD_Report.pdf`);
    } catch (error) {
      toast.error('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };


  const loadVectorStores = async () => {
    try {
      const response = await vectorStoresAPI.list();
      // Ensure response.data is always an array
      setVectorStores(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      setVectorStores([]);
    }
  };

  const loadVectorStoreAssignments = async () => {
    if (!sessionIdentifier) return;

    try {
      const response = await vectorStoresAPI.getSessionAssignments(sessionIdentifier);
      const assignments = response.data?.assignments || [];

      // Keep the name the API already returns alongside the id: the card looks
      // the store up in the user's own list, which is filtered by creator, so a
      // colleague's store -- perfectly usable by the engine -- was not found
      // there and showed as "None assigned".
      const describe = (assignment) => ({
        id: assignment.vector_store_id,
        name: assignment.vector_store_name
      });

      const assignmentMap = {};
      assignments.forEach(assignment => {
        if (assignment.dd_type_code) {
          assignmentMap[assignment.dd_type_code] = describe(assignment);
        }
      });

      // Assignments carrying no DD type used to be dropped here, so a store
      // assigned to the whole session showed as "None assigned" on every card
      // while the engine was in fact reading from it.
      const sessionWide = assignments.find(assignment => !assignment.dd_type_code);

      setVectorStoreAssignments(assignmentMap);
      setSessionWideVectorStore(sessionWide ? describe(sessionWide) : null);
    } catch (error) {
      // Silent fail - no vector stores assigned yet
      setVectorStoreAssignments({});
      setSessionWideVectorStore(null);
    }
  };

  function getOverallStatus(relevantDdTypes) {
    const total = relevantDdTypes ? relevantDdTypes.length : 0;

    if (!sessionProgress || Object.keys(sessionProgress).length === 0 || total === 0) {
      return { status: 'not_started', completed: 0, total, percentage: 0 };
    }

    // Only the DD types actually shown. sessionProgress holds every execution of
    // the session, including ones since deactivated or removed from the session:
    // averaging those over the smaller displayed count gave "3 / 2 Complete
    // (150%)" and a bar running past its rail.
    const shown = new Set(relevantDdTypes.map(ddType => ddType.code));
    const progressList = Object.values(sessionProgress)
      .filter(p => !p.dd_type || shown.has(p.dd_type));

    // Calculate overall percentage based on actual progress, not just completed count
    const totalProgress = progressList.reduce((sum, p) => sum + (p.percentage || 0), 0);
    const percentage = total > 0 ? Math.min(Math.round(totalProgress / total), 100) : 0;

    // Same status rule as the Dashboard (utils/executionStatus); "complete"
    // counts finished runs, not a percentage the progress endpoint rounds.
    const completed = progressList.filter(p => FINISHED_STATUSES.includes(p.status)).length;
    const status = getSessionStatus(progressList, total);

    return { status, completed, total, percentage };
  };

  const handleAssignVectorStore = async (ddTypeCode, vectorStoreId) => {
    try {
      const ddType = ddTypes.find(dd => dd.code === ddTypeCode);
      await vectorStoresAPI.assignToSession(vectorStoreId, sessionIdentifier, {
        dd_type_id: ddType?.id
      });

      setVectorStoreAssignments(prev => ({
        ...prev,
        [ddTypeCode]: {
          id: vectorStoreId,
          name: vectorStores.find(vs => vs.id === vectorStoreId)?.name
        }
      }));

      toast.success(`Vector store assigned to ${ddType?.name || ddTypeCode}`);
    } catch (error) {
      toast.error('Failed to assign vector store');
    }
  };

  const handleRemoveVectorStoreAssignment = async (ddTypeCode) => {
    const perTypeStore = vectorStoreAssignments[ddTypeCode];
    try {
      // The card may be showing the session-wide store. That assignment carries
      // no DD type, so scoping the removal to one would leave it in place -- and
      // dropping it removes the documents from every type, hence the wording.
      await vectorStoresAPI.removeFromSession(
        (perTypeStore || sessionWideVectorStore)?.id,
        sessionIdentifier,
        perTypeStore ? ddTypeCode : null
      );

      if (perTypeStore) {
        setVectorStoreAssignments(prev => {
          const newAssignments = { ...prev };
          delete newAssignments[ddTypeCode];
          return newAssignments;
        });
        toast.success(`Vector store removed from ${ddTypes.find(dd => dd.code === ddTypeCode)?.name || ddTypeCode}`);
      } else {
        setSessionWideVectorStore(null);
        toast.success('Vector store removed from all DD types of this session');
      }
    } catch (error) {
      toast.error('Failed to remove vector store assignment');
    }
  };

  const handleBulkAssignVectorStore = async (vectorStoreId) => {
    try {
      const ddTypeCodes = relevantDdTypes.map(ddType => ddType.code);
      const vectorStoreName = vectorStores.find(vs => vs.id === vectorStoreId)?.name || 'vector store';

      // Assign to each DD type individually
      await Promise.all(
        ddTypeCodes.map(ddTypeCode => {
          const ddType = ddTypes.find(dd => dd.code === ddTypeCode);
          return vectorStoresAPI.assignToSession(vectorStoreId, sessionIdentifier, {
            dd_type_id: ddType?.id
          });
        })
      );

      const newAssignments = {};
      ddTypeCodes.forEach(code => {
        newAssignments[code] = { id: vectorStoreId, name: vectorStoreName };
      });

      setVectorStoreAssignments(prev => ({
        ...prev,
        ...newAssignments
      }));

      // Reset the dropdown
      setBulkAssignValue('');

      toast.success(`${vectorStoreName} assigned to all DD types`);
    } catch (error) {
      toast.error('Failed to bulk assign vector store');
      // Reset dropdown on error too
      setBulkAssignValue('');
    }
  };

  const handleDeleteSession = async () => {
    // Check if session status allows deletion
    if (session.status === 'in_progress' || session.status === 'completed') {
      toast.error(`Cannot delete session with status "${session.status}". Only sessions with status "created", "documents_uploaded", "failed", or "paused" can be deleted.`);
      return;
    }

    // Show confirmation dialog
    const confirmMessage = `Are you sure you want to delete session "${session.name}"?\n\nThis will permanently delete:\n- All answers and answer history\n- All executions and their responses\n- All vector store assignments\n\nThis action cannot be undone.`;

    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      await sessionAPI.delete(sessionIdentifier);
      toast.success('Session deleted successfully');
      navigate('/dashboard');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to delete session';
      toast.error(errorMessage);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" text="Loading session details..." />
        </div>
      </Layout>
    );
  }

  if (!session) {
    return (
      <Layout>
        <EmptyState
          title="Session not found"
          text="The requested session could not be found, or you do not have access to it."
          action={<Button variant="secondary" onClick={() => navigate('/')}>Back to Dashboard</Button>}
        />
      </Layout>
    );
  }

  // Parse selected DD types from session data
  function getSessionDdTypes() {
    if (session?.dd_types_json) {
      try {
        const selectedDdTypes = JSON.parse(session.dd_types_json);

        // Filter ddTypes to only include the ones selected for this session
        const filteredDdTypes = ddTypes.filter(ddType =>
          selectedDdTypes.some(selected => selected.code === ddType.code)
        );

        if (filteredDdTypes.length > 0) {
          return filteredDdTypes;
        }
      } catch (error) {
        console.error('Unreadable dd_types_json for this session:', error);
      }
    }

    // Fallback: the DD types this session actually ran. Showing the whole
    // library instead -- as this did when there was no progress yet -- put Start
    // buttons on questionnaires that were never part of the session.
    return ddTypes.filter(ddType => sessionProgress[ddType.code] !== undefined);
  };

  return (
    <Layout>
      <div className={pageLayout.container}>
        <PageHeader
          breadcrumb={[{ label: session.name || 'Session' }]}
          title={session.name}
          subtitle={session.description}
          meta={(
            <span className="tabular-nums" title={`Session code: ${session.session_code || `SES-${session.id}`}`}>
              Created {new Date(session.created_at).toLocaleDateString()}
              {session.company_name && ` · ${session.company_name}`}
              {session.management_company_name && ` · ${session.management_company_name}`}
            </span>
          )}
          actions={(
            <>
            {Object.values(sessionProgress).some(p => FINISHED_STATUSES.includes(p.status)) && (
              <Button
                variant="primary"
                size="sm"
                icon={DocumentArrowDownIcon}
                onClick={handleExportPdf}
                loading={exporting}
              >
                Export PDF
              </Button>
            )}
            <Button
              variant="danger"
              size="sm"
              icon={TrashIcon}
              onClick={handleDeleteSession}
              disabled={session.status === 'in_progress' || session.status === 'completed'}
              title={
                session.status === 'in_progress' || session.status === 'completed'
                  ? `Cannot delete session with status "${session.status}"`
                  : 'Delete session'
              }
            >
              Delete Session
            </Button>
            </>
          )}
        />

        {/* New Session Welcome Message */}
        {location.state?.newSession && (
          <div className="alert alert-success">
            <div className="flex items-start space-x-3">
              <CheckCircleIcon className="w-5 h-5 mt-0.5 flex-shrink-0 text-theme-success" />
              <div>
                <h3 className="text-sm font-medium text-theme-success">Session created</h3>
                <p className="text-sm text-content-secondary mt-1">
                  Your due diligence session is ready. Next step: Create and assign document collections below to enable AI-powered analysis.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Overall Progress */}
        <div className={panel.base}>
          <div className={`${panel.header} flex items-center justify-between gap-4`}>
            <div>
              <h2 className={sectionHeader.title}>Overall Progress</h2>
              <p className="text-sm text-content-secondary mt-1">
                Track the completion status of your due diligence analysis
              </p>
              {progressStale && (
                <p className="text-sm text-theme-warning mt-1 flex items-center gap-1.5">
                  <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0" />
                  Live updates interrupted — the figures below may be out of date.
                </p>
              )}
            </div>
            <StatusBadge status={overallStatus.status} size="lg" className="flex-shrink-0 tabular-nums">
              {overallStatus.completed} / {overallStatus.total} Complete ({overallStatus.percentage}%)
            </StatusBadge>
          </div>

          <div className={panel.body}>
            <div className="relative">
              <div className="w-full bg-surface-hover rounded-full h-2 overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ease-out ${
                    overallStatus.status === 'completed' ? 'bg-theme-success' :
                    overallStatus.status === 'in_progress' ? 'bg-gradient-to-r from-accent-blue to-accent-green' :
                    'bg-content-muted/40'
                  }`}
                  style={{ width: `${overallStatus.percentage}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-xs text-content-muted tabular-nums mt-2">
                <span>0%</span>
                <span className="font-medium text-content">{overallStatus.percentage}%</span>
                <span>100%</span>
              </div>
            </div>

            {overallStatus.status === 'completed' && (
              <div className="mt-4 alert alert-success">
                <p className="text-sm flex items-center">
                  <CheckCircleIcon className="w-5 h-5 mr-2 flex-shrink-0" />
                  All due diligence types are complete.
                </p>
              </div>
            )}

            {Object.values(sessionProgress).some(p => p.status === 'in_progress') && (
              <div className="mt-4 alert alert-info">
                <p className="text-sm flex items-center">
                  <ClockIcon className="w-5 h-5 mr-2 flex-shrink-0 animate-pulse" />
                  Processing in progress... Only one due diligence type can run at a time.
                </p>
              </div>
            )}
          </div>
        </div>
        {/* DD Type Cards */}
        <div>
          <div className="flex items-center justify-between gap-4 mb-6">
            <div className="flex-1 min-w-0">
              <div className={sectionHeader.wrapper}>
                <h2 className={sectionHeader.title}>Due Diligence Analysis</h2>
                <div className={sectionHeader.hairline} />
              </div>
              <span className="mt-1 block text-sm text-content-muted">
                {relevantDdTypes.length} type{relevantDdTypes.length !== 1 ? 's' : ''} configured
              </span>
            </div>

            {vectorStores.length > 0 && (
              <div className="flex items-center gap-3 flex-shrink-0">
                <span className="text-xs text-content-muted">Assign to all:</span>
                <select
                  value={bulkAssignValue}
                  onChange={(e) => {
                    setBulkAssignValue(e.target.value);
                    if (e.target.value) {
                      handleBulkAssignVectorStore(e.target.value);
                    }
                  }}
                  className="form-input px-3 py-1 text-xs"
                >
                  <option value="">Select vector store...</option>
                  {vectorStores.map(store => (
                    <option key={store.id} value={store.id}>
                      {store.name} ({store.file_count} files)
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {relevantDdTypes.map(ddType => {
            const progress = sessionProgress[ddType.code];
            const canStart = canStartDD(ddType);

            return (
              <div key={ddType.code} className="relative">
                <DDCard
                  ddType={ddType}
                  progress={progress}
                  onStart={canStart ? handleStartDD : null}
                  onResume={handleResumeDD}
                  onPause={handlePauseDD}
                  onView={handleViewDD}
                  onSynthesis={handleSynthesisDD}
                  disabled={!canStart && progress?.status !== 'in_progress'}
                  vectorStores={vectorStores}
                  assignedVectorStore={(() => {
                    // The assignment itself is the fallback: it carries id and
                    // name, so a store the current user cannot list still shows.
                    const assigned = vectorStoreAssignments[ddType.code] || sessionWideVectorStore;
                    if (!assigned) return undefined;
                    return vectorStores.find(vs => vs.id === assigned.id) || assigned;
                  })()}
                  onAssignVectorStore={handleAssignVectorStore}
                  onRemoveVectorStore={handleRemoveVectorStoreAssignment}
                />

                {/* Sequential Processing Info */}
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
    </Layout>
  );
};

export default SessionDetail;
