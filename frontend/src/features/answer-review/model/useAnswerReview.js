import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { answersAPI } from '@/entities/answer';
import { errorMessage } from '@/shared/api';
import { useAnswerEditor } from './useAnswerEditor';
import { useVersionHistory } from './useVersionHistory';

/**
 * What a reviewer does to the answers of a questionnaire: approve one (or send
 * it back to review), edit it, read and restore its versions, regenerate it.
 *
 * onChange(answerId, changes): an answer changed, keep it on screen;
 * setStatus(answerId, status): store a new review status;
 * reload(): fetch the answers again, behind the page;
 * onDocumentAdded(): a regeneration added its document to the session's collection.
 */
export const useAnswerReview = ({ onChange, setStatus, reload, onDocumentAdded }) => {
  const history = useVersionHistory();
  const editor = useAnswerEditor(onChange, history.fetchVersionHistory);
  const [statusPending, setStatusPending] = useState(null);
  const [regenerateTarget, setRegenerateTarget] = useState(null);
  const [regeneratingId, setRegeneratingId] = useState(null);

  const toggleStatus = async answer => {
    setStatusPending(answer.id);
    try {
      await setStatus(answer.id, answer.status === 'approved' ? 'needs_review' : 'approved');
    } catch {
      toast.error('Failed to update the answer status');
    } finally {
      setStatusPending(null);
    }
  };

  const revert = (answerId, version) => history.revertToVersion(answerId, version, reload);

  // The modal gathers the optional guidance; the call happens on submit, and
  // waits for the new answer.
  const regenerate = async ({ instruction, referenceUrl, file }) => {
    const answerId = regenerateTarget;
    if (!answerId) return;
    setRegeneratingId(answerId);
    try {
      await answersAPI.regenerate(answerId, { instruction, referenceUrl, file });
      await reload();
      if (history.showVersionHistory[answerId]) await history.fetchVersionHistory(answerId);
      setRegenerateTarget(null);
      toast.success('Answer regenerated.');
      // The document went into the session's collection, which may be new.
      if (file) onDocumentAdded?.();
    } catch (error) {
      toast.error(errorMessage(error, 'Regeneration failed. Please try again.'));
    } finally {
      setRegeneratingId(null);
    }
  };

  const closeRegenerate = useCallback(() => setRegenerateTarget(null), []);

  return {
    editor,
    history,
    toggleStatus,
    statusPending,
    revert,
    regeneration: {
      targetId: regenerateTarget,
      regeneratingId,
      open: setRegenerateTarget,
      close: closeRegenerate,
      submit: regenerate,
    },
  };
};
