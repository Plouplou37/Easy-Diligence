import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  PlayIcon,
  PauseIcon,
  EyeIcon,
  DocumentTextIcon,
  SparklesIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline';
import { MiniProgressBar } from './ProgressBar';
import { questionsAPI } from '../services/api';
import { Badge, Button, StatusBadge, panel } from './ui';
import { getToneStyles } from '../utils/statusStyles';
import { FINISHED_STATUSES } from '../utils/executionStatus';
import { getDdTypeIcon } from '../utils/ddTypeIcon';

// Component to fetch and display section data with question counts
const SectionBarsWithData = ({ ddType, parentProgress }) => {
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  // Distinguishes "could not load" from "no sections", which the placeholder
  // used to conflate -- it asserted "Section not configured" over a DD type
  // whose 27 sections were sitting in the database.
  const [failed, setFailed] = useState(false);

  const ddTypeCode = typeof ddType === 'object' ? ddType.code : ddType;
  const parentStatus = parentProgress?.status;

  useEffect(() => {
    const fetchSectionData = async () => {
      try {
        if (!ddTypeCode) return;

        // Through the shared client: a raw fetch bypassed the 401 interceptor,
        // so an expired token degraded silently into the placeholder below.
        const response = await questionsAPI.getDdTypes();
        const matched = response.data?.find(t => t.code === ddTypeCode);

        if (matched) {
          // Group questions by section and count them
          const isParentCompleted = FINISHED_STATUSES.includes(parentStatus);
          setSections((matched.sections || []).map(section => ({
            name: section.title,
            total_questions: section.questions?.length || 0,
            questions_completed: isParentCompleted ? (section.questions?.length || 0) : 0,
            status: isParentCompleted ? 'completed' : 'not_started'
          })));
        } else {
          setFailed(true);
        }
      } catch (error) {
        setFailed(true);
      } finally {
        setLoading(false);
      }
    };

    fetchSectionData();
    // On the code and the status, not the objects: the session page rebuilds
    // its progress object on every poll, which refetched every DD type's whole
    // structure every 3 s.
  }, [ddTypeCode, parentStatus]);

  if (loading) {
    return (
      <div className="flex space-x-1">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="h-6 flex-1 rounded-md bg-surface-hover animate-pulse" />
        ))}
      </div>
    );
  }

  if (sections.length === 0) {
    return (
      <div className="h-6 flex items-center rounded-md bg-surface-bg px-2">
        <span className="text-[11px] text-content-muted">
          {failed ? 'Sections unavailable — reload the page' : 'No section in this DD type'}
        </span>
      </div>
    );
  }

  return (
    <div className="flex space-x-1 overflow-x-auto pb-1 custom-scrollbar">
      {sections.map((section, index) => {
        const questionsCompleted = section.questions_completed || 0;
        const totalQuestions = section.total_questions || 0;
        const percentage = totalQuestions > 0 ? Math.round((questionsCompleted / totalQuestions) * 100) : 0;

        return (
          <div
            key={index}
            className="relative h-6 flex-1 min-w-[90px] rounded-md overflow-hidden"
            title={`${section.name}: ${questionsCompleted}/${totalQuestions} questions (${percentage}%)`}
          >
            <div className="absolute inset-0 bg-surface-hover" />
            <div
              className="absolute inset-y-0 left-0 rounded-md transition-all duration-300 bg-content-muted/40"
              style={{ width: `${percentage}%` }}
            />
            <div className="absolute inset-0 flex items-center justify-between px-2 gap-2">
              <span className="text-[10px] font-medium text-content whitespace-nowrap tabular-nums">
                {questionsCompleted}/{totalQuestions}
              </span>
              <span className="text-[10px] font-bold text-content tabular-nums">
                {percentage}%
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const DDCard = ({
  ddType,
  progress,
  onStart,
  onResume,
  onPause,
  onView,
  onSynthesis,
  disabled = false,
  // Vector store props
  vectorStores = [],
  assignedVectorStore = null,
  onAssignVectorStore = null,
  onRemoveVectorStore = null
}) => {
  // Support both old string format and new object format
  const isObject = typeof ddType === 'object';
  const ddTypeCode = isObject ? ddType.code : ddType;
  const ddTypeName = isObject ? ddType.name : ddType;
  const ddTypeDescription = isObject ? ddType.description : `Due diligence for ${ddType}`;
  // Outline icon guessed from the name: the stored `icon` is an emoji.
  const DdTypeIcon = getDdTypeIcon(ddType);
  // A deactivated type stays on screen so the answers already produced under it
  // remain readable; it just cannot be run again.
  const isInactive = isObject && ddType.is_active === false;

  const getActionButton = () => {
    const status = progress?.status || 'not_started';

    // Offering "Start" on a validated DD invited relaunching a finished run.
    if (FINISHED_STATUSES.includes(status)) {
      return (
        <div className="flex space-x-2">
          {onSynthesis && (
            <Button
              variant="ghost"
              size="sm"
              icon={SparklesIcon}
              onClick={() => onSynthesis(ddTypeCode)}
            >
              Synthesis
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            icon={EyeIcon}
            onClick={() => onView && onView(ddTypeCode)}
          >
            Review Answers
          </Button>
        </div>
      );
    }

    if (status === 'in_progress') {
      return (
        <div className="flex space-x-2">
          <Button
            variant="secondary"
            size="sm"
            icon={PauseIcon}
            onClick={() => onPause && onPause(ddTypeCode)}
            disabled={disabled}
          >
            Pause
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={EyeIcon}
            onClick={() => onView && onView(ddTypeCode)}
          >
            Review Answers
          </Button>
        </div>
      );
    }

    if (status === 'failed' || status === 'paused') {
      return (
        <Button
          variant="primary"
          size="sm"
          icon={PlayIcon}
          onClick={() => onResume && onResume(ddTypeCode)}
          disabled={disabled}
        >
          Resume
        </Button>
      );
    }

    // A deactivated type that was never run has nothing to offer: no Start (it
    // is retired) and no View (there is no answer behind it).
    if (isInactive) {
      return (
        <span className="text-xs text-content-muted italic">
          Deactivated
        </span>
      );
    }

    // not_started
    return (
      <Button
        variant="primary"
        size="sm"
        icon={PlayIcon}
        onClick={() => onStart && onStart(ddTypeCode)}
        disabled={disabled}
      >
        Start
      </Button>
    );
  };

  const percentage = progress?.percentage || 0;
  const questionsCompleted = progress?.questions_completed || 0;
  const totalQuestions = progress?.total_questions || 0;
  const sectionsProgress = progress?.sections_progress || [];
  const activeSection = sectionsProgress.find(section => section.status === 'in_progress');
  const timeElapsed = progress?.time_elapsed || 0;
  const tokensUsed = progress?.tokens_used || 0;
  const elapsedTitle = tokensUsed > 0
    ? `Time spent answering · ${tokensUsed.toLocaleString()} tokens`
    : 'Time spent answering';
  const answersWithDocuments = progress?.answers_with_documents || 0;
  const answersCounted = progress?.answers_counted || 0;


  // Helper function to format time
  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  // Calculate section progress stats
  const getSectionStats = () => {
    if (!sectionsProgress.length) return null;

    const completed = sectionsProgress.filter(s => s.status === 'completed').length;
    const inProgress = sectionsProgress.filter(s => s.status === 'in_progress').length;
    const total = sectionsProgress.length;

    return { completed, inProgress, total };
  };

  const sectionStats = getSectionStats();

  return (
    <div className={`${panel.base} overflow-hidden hover:shadow-md transition-shadow duration-200 h-[28rem]`}>
      <div className={panel.rail} />
      {/* The card height is fixed (28rem): paddings, header height and the
          compact buttons are sized so a running DD -- stats, current question
          and actions -- still fits inside it. */}
      <div className="pl-6 pr-5 py-5 h-full flex flex-col">
        {/* Header - Fixed height to ensure alignment */}
        <div className="h-[4.5rem] flex items-center justify-between mb-4">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <div className="p-2 rounded-lg bg-surface-bg flex-shrink-0">
              <DdTypeIcon className="w-5 h-5 text-content-secondary" />
            </div>
            <div className="min-w-0 flex-1">
              {/* line-clamp with no title left the full name unreachable --
                  "INVESTMENT DUE DILIGENCE (2026 EDITION)" reads as
                  "INVESTMENT DUE DILIGENCE..." and nothing recovers the rest. */}
              <h3 className="text-fluid-md font-medium text-content line-clamp-1" title={ddTypeName}>
                {ddTypeName}
              </h3>
              <p className="text-sm text-content-muted line-clamp-2 leading-tight" title={ddTypeDescription}>
                {ddTypeDescription}
              </p>
            </div>
          </div>
          <div className="flex-shrink-0 ml-3 flex items-center gap-2">
            {isInactive && (
              <span title="This DD type has been deactivated: it is no longer offered for new sessions. Existing answers stay available.">
                <Badge variant="warning">Inactive</Badge>
              </span>
            )}
            <StatusBadge status={progress?.status || 'not_started'} />
          </div>
        </div>

        {/* Content Area - Fixed height container with consistent positioning */}
        <div className="flex-1 space-y-3">
          {/* Progress Section */}
          <div className="min-h-[80px]">
            {/* Always show progress structure, even for not_started */}
            <div className="space-y-3">
              {/* Overall Progress */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="eyebrow leading-4">Overall Progress</span>
                  <span className="text-xs text-content-muted tabular-nums">
                    {totalQuestions > 0 ? `${questionsCompleted}/${totalQuestions}` : 'Not configured'}
                  </span>
                </div>
                {totalQuestions > 0 ? (
                  <MiniProgressBar
                    current={questionsCompleted}
                    total={totalQuestions}
                    status={progress?.status || 'not_started'}
                  />
                ) : (
                  <div className="w-full bg-surface-hover rounded-full h-1.5">
                    <div className="bg-content-muted/40 h-1.5 rounded-full" style={{ width: '0%' }}></div>
                  </div>
                )}
              </div>

              {/* Section Progress or Placeholder */}
              <div>
                <div className="flex justify-between items-center mb-1 gap-2">
                  {/* Which section is being worked on. The tiles below carry
                      only counters, and with 27 of them (the BETA questionnaire)
                      the name was reachable solely by hovering each one. */}
                  <span className="eyebrow leading-4 truncate" title={activeSection?.name}>
                    {activeSection ? `Sections — ${activeSection.name}` : 'Sections'}
                  </span>
                  <span className="text-xs text-content-muted flex-shrink-0">
                    {sectionStats ? `${sectionStats.completed}/${sectionStats.total} completed` : 'Ready to start'}
                  </span>
                </div>

                {/* Section Progress Bars with Embedded Info */}
                {sectionsProgress.length > 0 ? (
                  <div className="flex space-x-1 overflow-x-auto pb-1 custom-scrollbar">
                    {sectionsProgress.map((section, index) => {
                      const questionsCompleted = section.questions_completed || 0;
                      const totalQuestions = section.total_questions || 0;
                      const percentage = totalQuestions > 0 ? Math.round((questionsCompleted / totalQuestions) * 100) : 0;

                      return (
                        <div
                          key={index}
                          className="relative h-6 flex-1 min-w-[90px] rounded-md overflow-hidden"
                          title={`${section.name || `Section ${index + 1}`}: ${questionsCompleted}/${totalQuestions} questions (${percentage}%)`}
                        >
                          {/* Background */}
                          <div className="absolute inset-0 bg-surface-hover" />

                          {/* Progress fill -- translucent tones, so the counters
                              drawn over it stay readable in both themes */}
                          <div
                            className={`absolute inset-y-0 left-0 rounded-md transition-all duration-300 ${
                              section.status === 'completed' ? 'bg-theme-success/40' :
                              section.status === 'in_progress' ? 'bg-accent-blue/40 animate-pulse' :
                              percentage > 0 ? 'bg-theme-warning/40' :
                              'bg-content-muted/40'
                            }`}
                            style={{ width: `${percentage}%` }}
                          />

                          {/* Text overlay */}
                          <div className="absolute inset-0 flex items-center justify-between px-2 gap-2">
                            <span className="text-[10px] font-medium text-content whitespace-nowrap tabular-nums">
                              {questionsCompleted}/{totalQuestions}
                            </span>
                            <span className="text-[10px] font-bold text-content tabular-nums">
                              {percentage}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  // Fetch and show actual sections when no progress data is available
                  <SectionBarsWithData ddType={ddType} parentProgress={progress} />
                )}
              </div>
            </div>
          </div>

          {/* Analytics & Status Section */}
          <div className="min-h-[80px]">
            {/* Show analytics for active states, simple info for not_started */}
            {progress?.status === 'not_started' ? (
              <div className={`alert p-2 ${isInactive ? 'alert-warning' : 'alert-info'}`}>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isInactive ? 'bg-theme-warning' : 'bg-accent-blue'}`}></div>
                  <span className="text-xs font-medium">
                    {isInactive
                      ? 'This DD type is deactivated and can no longer be run'
                      : 'Click Start to begin analysis'}
                  </span>
                </div>
              </div>
            ) : (progress?.status === 'in_progress' || FINISHED_STATUSES.includes(progress?.status)) && (
              <div className="space-y-3">
                {/* Quick Stats */}
                <div className="grid grid-cols-2 gap-2">
                  {/* Elapsed (token count in the tooltip: a technical figure) */}
                  <div className="text-center p-2 bg-surface-bg rounded-md" title={elapsedTitle}>
                    <ClockIcon className="w-3 h-3 mx-auto mb-1 text-content-muted" />
                    <div className="text-xs text-content tabular-nums">
                      {timeElapsed > 0 ? formatTime(timeElapsed) : 'Starting...'}
                    </div>
                    <div className="eyebrow-light leading-4">elapsed</div>
                  </div>

                  {/* Answers resting on the assigned documents rather than the
                      web alone -- the question the whole RAG setup exists for.
                      This slot used to show an average confidence whose source
                      is no longer written, so it could only read "N/A". */}
                  <div className="text-center p-2 bg-surface-bg rounded-md" title="Answers citing the assigned documents">
                    <DocumentTextIcon className="w-3 h-3 mx-auto mb-1 text-content-muted" />
                    <div className="text-xs text-content tabular-nums">
                      {answersCounted > 0 ? `${answersWithDocuments}/${answersCounted}` : '—'}
                    </div>
                    <div className="eyebrow-light leading-4">from docs</div>
                  </div>
                </div>

                {/* Current Status */}
                {progress?.status === 'in_progress' && progress.current_section && (
                  <div className="alert alert-info p-2">
                    <div className="flex items-center space-x-2">
                      <div className="live-indicator animate-pulse flex-shrink-0"></div>
                      <span className="text-xs font-medium">
                        {progress.current_section}
                      </span>
                    </div>
                    {progress.current_question && (
                      <p className="text-xs text-content-secondary mt-1 ml-4">
                        {progress.current_question}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Error Info */}
            {progress?.status === 'failed' && progress.last_error && (
              <div className="alert alert-error p-3">
                <div className="flex">
                  <XCircleIcon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div className="ml-2 flex-1">
                    <span className="text-sm font-medium">Error:</span>
                    <p className="text-sm text-content-secondary mt-1 break-words">
                      {progress.last_error}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Completed Status */}
            {FINISHED_STATUSES.includes(progress?.status) && (
              <div className="alert alert-success p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <CheckCircleIcon className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      Analysis completed
                    </span>
                  </div>
                  {timeElapsed > 0 && (
                    <span className="text-xs tabular-nums">
                      in {formatTime(timeElapsed)}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Vector Store Assignment. Shown as soon as there is either a store to
            pick from or one already assigned: gating the whole block on the
            list made an existing assignment vanish whenever that list failed
            to load. */}
        {(vectorStores.length > 0 || assignedVectorStore) && (
          <div>
            {assignedVectorStore ? (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="eyebrow leading-4">
                    Documents
                  </span>
                  {/* file_count is unknown when the store is only known through
                      the assignment, or when OpenAI could not be reached. */}
                  <span className="text-xs text-content-muted">
                    {typeof assignedVectorStore.file_count === 'number'
                      ? `${assignedVectorStore.file_count} files`
                      : 'assigned'}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className={`inline-flex items-center gap-1 min-w-0 px-2 py-0.5 rounded-xl border text-xs font-medium ${getToneStyles('success').badge}`}>
                    <BookOpenIcon className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{assignedVectorStore.name}</span>
                  </span>
                  {!disabled && progress?.status !== 'in_progress' && onRemoveVectorStore && (
                    <button
                      onClick={() => onRemoveVectorStore(ddTypeCode)}
                      className="pill-action"
                      data-variant="danger"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="eyebrow leading-4">
                    Documents
                  </span>
                  <span className="flex items-center gap-2">
                    <Link to="/vector-stores" className="text-xs text-link">Manage stores</Link>
                    <Badge variant="warning" icon={ExclamationTriangleIcon}>
                      None assigned
                    </Badge>
                  </span>
                </div>
                {!disabled && progress?.status !== 'in_progress' && onAssignVectorStore ? (
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        onAssignVectorStore(ddTypeCode, e.target.value);
                      }
                    }}
                    className="form-input w-full px-2 py-1 text-xs"
                  >
                    <option value="">Select vector store...</option>
                    {vectorStores.map(store => (
                      <option key={store.id} value={store.id}>
                        {store.name} ({store.file_count} files)
                      </option>
                    ))}
                  </select>
                ) : (disabled || progress?.status === 'in_progress') && (
                  <span className="text-xs text-content-muted">
                    Cannot change while processing
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Actions - Fixed at bottom */}
        <div className="flex justify-end pt-3 border-t border-border">
          {getActionButton()}
        </div>
      </div>
    </div>
  );
};

export default DDCard;
