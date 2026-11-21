import { useState } from 'react';
import toast from 'react-hot-toast';
import { processingAPI } from '@/entities/execution';

// The statuses a run can be (re)started from.
const STARTABLE = ['not_started', 'failed', 'paused'];

/**
 * Starting, pausing and resuming the DD type runs of a session. One run at a
 * time: a session's runs share its OpenAI quota and its vector stores.
 *
 * progressByCode: the session's progress, by DD type code; onChange: reload it.
 * `pending`: the code of the DD type whose request is on its way.
 */
export const useDdRunControl = ({ sessionId, progressByCode, ddTypes, onChange }) => {
  const [pending, setPending] = useState(null);
  const isRunning = Object.values(progressByCode).some(run => run.status === 'in_progress');

  // A deactivated type stays visible so its answers remain readable, but it
  // cannot be run any more: that is what deactivating it means.
  const canStart = ddType => {
    if (ddType.is_active === false || isRunning) return false;
    const run = progressByCode[ddType.code];
    return !run || STARTABLE.includes(run.status);
  };

  // Toasts name the questionnaire, not its internal code.
  const nameOf = code => ddTypes.find(ddType => ddType.code === code)?.name || code;

  const act = (call, done, failure) => async code => {
    setPending(code);
    try {
      await call(sessionId, code);
      toast.success(`${done} ${nameOf(code)}`);
      await onChange();
    } catch {
      toast.error(failure);
    } finally {
      setPending(null);
    }
  };

  return {
    isRunning,
    canStart,
    pending,
    start: act(processingAPI.start, 'Started', 'Failed to start the questionnaire'),
    resume: act(processingAPI.resume, 'Resumed', 'Failed to resume the questionnaire'),
    pause: act(processingAPI.pause, 'Paused', 'Failed to pause the questionnaire'),
  };
};
