import { EyeIcon, PauseIcon, PlayIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { FINISHED_STATUSES } from '@/entities/execution';
import { Button } from '@/shared/ui';

/** What can be done with the run now: start, pause, resume, or read its results. */
export const RunActions = ({
  code,
  status,
  isInactive,
  disabled,
  onStart,
  onResume,
  onPause,
  onView,
  onSynthesis,
}) => {
  const review = (
    <Button variant="secondary" size="sm" icon={EyeIcon} onClick={() => onView?.(code)}>
      Review Answers
    </Button>
  );
  const synthesis = onSynthesis && (
    <Button variant="ghost" size="sm" icon={SparklesIcon} onClick={() => onSynthesis(code)}>
      Synthesis
    </Button>
  );

  // A finished run is read, not relaunched.
  if (FINISHED_STATUSES.includes(status)) {
    return (
      <div className="flex space-x-2">
        {synthesis}
        {review}
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
          onClick={() => onPause?.(code)}
          disabled={disabled}
        >
          Pause
        </Button>
        {review}
      </div>
    );
  }
  // Stopped half-way: the answers already written can be read, and summed up,
  // without resuming (and paying for) the rest. Without any answer, the
  // synthesis page says so.
  if (status === 'failed' || status === 'paused') {
    return (
      <div className="flex flex-wrap justify-end gap-2">
        {synthesis}
        {review}
        <Button
          variant="primary"
          size="sm"
          icon={PlayIcon}
          onClick={() => onResume?.(code)}
          disabled={disabled}
        >
          Resume
        </Button>
      </div>
    );
  }
  // A deactivated type never run has nothing to offer: it is retired, and
  // there is no answer behind it.
  if (isInactive) {
    return <span className="text-xs text-content-muted italic">Deactivated</span>;
  }
  return (
    <Button
      variant="primary"
      size="sm"
      icon={PlayIcon}
      onClick={() => onStart?.(code)}
      disabled={disabled}
    >
      Start
    </Button>
  );
};
