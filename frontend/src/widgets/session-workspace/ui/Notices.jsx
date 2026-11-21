import {
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { FOCUS_RING } from '../lib/focus';

// Whole class names, for Tailwind to find them.
const TONES = {
  success: 'alert-success',
  error: 'alert-error',
  info: 'alert-info',
  warning: 'alert-warning',
};

const Notice = ({ tone, icon: Icon, children, onDismiss }) => (
  <div className={`alert ${TONES[tone]} flex items-start gap-3`}>
    <Icon className="mt-0.5 h-5 w-5 shrink-0" />
    <div className="min-w-0 flex-1 text-sm">{children}</div>
    {onDismiss && (
      <button
        type="button"
        onClick={onDismiss}
        className={`-m-2 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg hover:bg-surface-hover ${FOCUS_RING}`}
        aria-label="Dismiss"
      >
        <XMarkIcon className="h-4 w-4" />
      </button>
    )}
  </div>
);

/**
 * What the reviewer should know about the selected questionnaire before
 * anything else: a new due diligence's next step, why a run stopped, why it
 * cannot start. `justCreated`: the due diligence was just created, with
 * `documentsAssigned` saying whether a document collection came with it.
 */
export const Notices = ({
  ddType,
  progress,
  runningName,
  justCreated,
  documentsAssigned,
  onDismissCreated,
}) => {
  const status = progress?.status || 'not_started';
  const stopped = status === 'not_started' || status === 'paused' || status === 'failed';
  const inactive = ddType?.is_active === false;

  return (
    <>
      {justCreated && (
        <Notice tone="success" icon={CheckCircleIcon} onDismiss={onDismissCreated}>
          <p className="font-medium">Due diligence created</p>
          <p className="mt-1 text-content-secondary">
            {documentsAssigned
              ? 'Documents are attached. Start the run when you are ready.'
              : 'Next step: assign a document collection in the Documents card on the left, so the AI can search it, then start the run.'}
          </p>
        </Notice>
      )}

      {/* The cause of the last failure, written for the user by the server. */}
      {status === 'failed' && progress?.last_error && (
        <Notice tone="error" icon={XCircleIcon}>
          <p className="font-medium">The run stopped</p>
          <p className="mt-1 wrap-break-word text-content-secondary">{progress.last_error}</p>
          {!inactive && (
            <p className="mt-1 text-content-secondary">
              Resume it to answer the remaining questions.
            </p>
          )}
        </Notice>
      )}

      {ddType && stopped && runningName && (
        <Notice tone="info" icon={ClockIcon}>
          {runningName} is running. One questionnaire runs at a time: this one can start once it is
          done.
        </Notice>
      )}

      {inactive && stopped && (
        <Notice tone="warning" icon={ExclamationTriangleIcon}>
          This questionnaire is deactivated and can no longer be run. Its answers stay available.
        </Notice>
      )}
    </>
  );
};
