import { CheckCircleIcon, ClockIcon, DocumentTextIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { FINISHED_STATUSES } from '@/entities/execution';
import { formatDuration } from '@/shared/lib/format';

/** Where the run stands: a prompt before it starts, its figures, its error. */
export const RunStatus = ({ progress, isInactive }) => {
  const status = progress?.status;
  const finished = FINISHED_STATUSES.includes(status);
  const elapsed = progress?.time_elapsed || 0;
  const tokens = progress?.tokens_used || 0;
  const withDocuments = progress?.answers_with_documents || 0;
  const counted = progress?.answers_counted || 0;

  return (
    <div className="min-h-[80px]">
      {status === 'not_started' ? (
        <div className={`alert p-2 ${isInactive ? 'alert-warning' : 'alert-info'}`}>
          <div className="flex items-center space-x-2">
            <div
              className={`w-2 h-2 rounded-full flex-shrink-0 ${isInactive ? 'bg-theme-warning' : 'bg-accent-blue'}`}
            ></div>
            <span className="text-xs font-medium">
              {isInactive
                ? 'This DD type is deactivated and can no longer be run'
                : 'Click Start to begin analysis'}
            </span>
          </div>
        </div>
      ) : (
        (status === 'in_progress' || finished) && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              {/* The token count, a technical figure, sits in the tooltip. */}
              <div
                className="text-center p-2 bg-surface-bg rounded-md"
                title={
                  tokens > 0
                    ? `Time spent answering · ${tokens.toLocaleString()} tokens`
                    : 'Time spent answering'
                }
              >
                <ClockIcon className="w-3 h-3 mx-auto mb-1 text-content-muted" />
                <div className="text-xs text-content tabular-nums">
                  {elapsed > 0 ? formatDuration(elapsed) : 'Starting...'}
                </div>
                <div className="eyebrow-light leading-4">elapsed</div>
              </div>
              {/* Answers resting on the assigned documents rather than on the web alone. */}
              <div
                className="text-center p-2 bg-surface-bg rounded-md"
                title="Answers citing the assigned documents"
              >
                <DocumentTextIcon className="w-3 h-3 mx-auto mb-1 text-content-muted" />
                <div className="text-xs text-content tabular-nums">
                  {counted > 0 ? `${withDocuments}/${counted}` : '—'}
                </div>
                <div className="eyebrow-light leading-4">from docs</div>
              </div>
            </div>
            {status === 'in_progress' && progress.current_section && (
              <div className="alert alert-info p-2">
                <div className="flex items-center space-x-2">
                  <div className="live-indicator animate-pulse flex-shrink-0"></div>
                  <span className="text-xs font-medium">{progress.current_section}</span>
                </div>
                {progress.current_question && (
                  <p className="text-xs text-content-secondary mt-1 ml-4">
                    {progress.current_question}
                  </p>
                )}
              </div>
            )}
          </div>
        )
      )}

      {status === 'failed' && progress.last_error && (
        <div className="alert alert-error p-3">
          <div className="flex">
            <XCircleIcon className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div className="ml-2 flex-1">
              <span className="text-sm font-medium">Error:</span>
              <p className="text-sm text-content-secondary mt-1 break-words">{progress.last_error}</p>
            </div>
          </div>
        </div>
      )}

      {finished && (
        <div className="alert alert-success p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircleIcon className="w-4 h-4" />
              <span className="text-sm font-medium">Analysis completed</span>
            </div>
            {elapsed > 0 && <span className="text-xs tabular-nums">in {formatDuration(elapsed)}</span>}
          </div>
        </div>
      )}
    </div>
  );
};
