import { PauseIcon, PlayIcon } from '@heroicons/react/24/outline';
import { FINISHED_STATUSES } from '@/entities/execution';
import { Button } from '@/shared/ui';

/**
 * What can be done with the questionnaire's run now: start, pause or resume
 * it (`runs`: useDdRunControl). A finished run is read, not relaunched; a
 * deactivated questionnaire never run has nothing to offer.
 */
export const RunButton = ({ ddType, progress, runs, size = 'lg' }) => {
  const code = ddType.code;
  const status = progress?.status || 'not_started';
  const canStart = runs.canStart(ddType);
  // One run at a time, and none on a deactivated questionnaire.
  const disabled = !canStart && status !== 'in_progress';
  const busy = runs.pending === code;
  const why = runs.isRunning
    ? 'Another questionnaire is running: one runs at a time.'
    : 'This questionnaire is deactivated: it can no longer be run.';

  if (FINISHED_STATUSES.includes(status)) return null;
  if (status === 'in_progress') {
    return (
      <Button
        variant="secondary"
        size={size}
        icon={PauseIcon}
        onClick={() => runs.pause(code)}
        loading={busy}
      >
        Pause
      </Button>
    );
  }
  // Stopped half-way: the rest of the questions are answered from where it stopped.
  if (status === 'failed' || status === 'paused') {
    return (
      <Button
        variant="primary"
        size={size}
        icon={PlayIcon}
        onClick={() => runs.resume(code)}
        disabled={disabled}
        loading={busy}
        title={disabled ? why : undefined}
      >
        Resume
      </Button>
    );
  }
  if (ddType.is_active === false) return null;
  return (
    <Button
      variant="primary"
      size={size}
      icon={PlayIcon}
      onClick={() => runs.start(code)}
      disabled={disabled}
      loading={busy}
      title={disabled ? why : undefined}
    >
      Start
    </Button>
  );
};
