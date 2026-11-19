import toast from 'react-hot-toast';
import { processingAPI } from '@/entities/execution';

// The statuses a run can be (re)started from.
const STARTABLE = ['not_started', 'failed', 'paused'];

/**
 * Starting, pausing and resuming the DD type runs of a session. One run at a
 * time: a session's runs share its OpenAI quota and its vector stores.
 *
 * progressByCode: the session's progress, by DD type code; onChange: reload it.
 */
export const useDdRunControl = ({ sessionId, progressByCode, ddTypes, onChange }) => {
  const isRunning = Object.values(progressByCode).some(run => run.status === 'in_progress');

  // A deactivated type stays visible so its answers remain readable, but it
  // cannot be run any more: that is what deactivating it means.
  const canStart = ddType => {
    if (ddType.is_active === false || isRunning) return false;
    const run = progressByCode[ddType.code];
    return !run || STARTABLE.includes(run.status);
  };

  // Toasts name the DD type, not its internal code.
  const nameOf = code => ddTypes.find(ddType => ddType.code === code)?.name || code;

  const act = (call, done, failure) => async code => {
    try {
      await call(sessionId, code);
      toast.success(`${done} ${nameOf(code)}`);
      await onChange();
    } catch {
      toast.error(failure);
    }
  };

  return {
    isRunning,
    canStart,
    start: act(processingAPI.start, 'Started', 'Failed to start DD processing'),
    resume: act(processingAPI.resume, 'Resumed', 'Failed to resume DD processing'),
    pause: act(processingAPI.pause, 'Paused', 'Failed to pause DD processing'),
  };
};
