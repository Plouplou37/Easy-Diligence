import {
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ListBulletIcon,
} from '@heroicons/react/24/outline';
import { ExportPdfButton, SessionMenu } from '@/features/session-actions';
import { formatDuration } from '@/shared/lib/format';
import { Badge, Breadcrumb, Button, StatusBadge } from '@/shared/ui';
import { RunButton } from './RunButton';

/** The run's figures, on one line: status, answered, time, tokens. */
const StatusLine = ({ ddType, progress, questionCount, stale }) => {
  const status = progress?.status || 'not_started';
  const done = progress?.questions_completed || 0;
  const total = progress?.total_questions || questionCount || 0;
  const elapsed = progress?.time_elapsed || 0;
  const tokens = progress?.tokens_used || 0;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-content-secondary">
      {ddType && (
        <>
          <StatusBadge status={status} />
          {ddType.is_active === false && (
            <span title="This questionnaire has been deactivated: it is no longer offered for new due diligences. Its answers stay available.">
              <Badge variant="warning">Inactive</Badge>
            </span>
          )}
          <span className="tabular-nums">
            {done} of {total} answered
          </span>
          {elapsed > 0 && (
            <span className="tabular-nums" title="Time spent answering, pauses left out">
              {formatDuration(elapsed)} of work, pauses left out
            </span>
          )}
          {tokens > 0 && <span className="tabular-nums">{tokens.toLocaleString()} tokens</span>}
        </>
      )}
      {/* The poll is the only thing that moves this page while a run goes on:
          when it stops answering, say so rather than look stalled. */}
      {stale && (
        <span className="inline-flex items-center gap-1.5 text-theme-warning">
          <ExclamationTriangleIcon className="h-4 w-4 shrink-0" />
          Live updates interrupted: the figures may be out of date.
        </span>
      )}
    </div>
  );
};

/** The progress of the whole due diligence: every questionnaire of it. */
const OverallProgress = ({ overall, multiple }) => {
  const complete = overall.status === 'completed';
  return (
    <div>
      <div
        role="progressbar"
        aria-label={multiple ? 'Progress of the due diligence' : 'Questions answered'}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={overall.percentage}
        className="h-1.5 overflow-hidden rounded-full bg-surface-hover"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-500 ease-out ${complete ? 'bg-theme-success' : 'bg-primary'}`}
          style={{ width: `${overall.percentage}%` }}
        />
      </div>
      {multiple && (
        <p className="mt-1.5 text-xs text-content-muted tabular-nums">
          {complete
            ? 'Every questionnaire is finished.'
            : `All questionnaires: ${overall.completed} of ${overall.total} finished · ${overall.percentage}%`}
        </p>
      )}
    </div>
  );
};

/**
 * The top of the workspace: where it is, the due diligence, the figures and
 * the actions of the selected questionnaire, and the overall progress.
 */
export const WorkspaceHeader = ({
  session,
  sessionId,
  ddType,
  progress,
  questionCount,
  overall,
  multiple,
  stale,
  runs,
  canExport,
  tab,
  onTabChange,
}) => {
  const showingSynthesis = tab === 'synthesis';
  return (
    <header className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <Breadcrumb
            items={[{ label: session.company_name || session.name || 'Due diligence' }]}
          />
          <h1
            className="text-2xl font-bold leading-tight tracking-tight text-content"
            title={`Code: ${session.session_code || `SES-${session.id}`}`}
          >
            {session.name || session.company_name}
          </h1>
          {session.description && (
            <p className="mt-1 line-clamp-2 text-sm text-content-secondary">
              {session.description}
            </p>
          )}
          <StatusLine
            ddType={ddType}
            progress={progress}
            questionCount={questionCount}
            stale={stale}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {ddType && (
            <Button
              variant="secondary"
              size="lg"
              icon={showingSynthesis ? ListBulletIcon : DocumentTextIcon}
              onClick={() => onTabChange(showingSynthesis ? 'questions' : 'synthesis')}
            >
              {showingSynthesis ? 'Questions' : 'Synthesis'}
            </Button>
          )}
          <ExportPdfButton
            sessionId={sessionId}
            size="lg"
            disabled={!canExport}
            title={canExport ? undefined : 'Nothing to export yet: no questionnaire has been run.'}
          />
          {ddType && <RunButton ddType={ddType} progress={progress} runs={runs} />}
          <SessionMenu session={session} sessionId={sessionId} status={overall.status} size="lg" />
        </div>
      </div>

      <OverallProgress overall={overall} multiple={multiple} />
    </header>
  );
};
