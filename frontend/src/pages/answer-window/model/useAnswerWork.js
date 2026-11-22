import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { answersAPI, parseSourcesFromString } from '@/entities/answer';
import { useAnswerDraft, useVersionHistory } from '@/features/answer-review';
import { errorMessage } from '@/shared/api';
import { publishAnswerChange, useAnswerChanges } from '@/shared/lib/answer-sync';
import { useConfirm } from '@/shared/lib/confirm';

// The lists call the answer's text `text` (useQuestionnaireReview): the same here.
const withText = answer => ({ ...answer, text: answer.answer_text });

/**
 * One answer worked on in a window of its own: the answer as the server has
 * it, its draft (useAnswerDraft) and its versions, and what changes it: save,
 * approve or send back to review, revert, regenerate. Each change is told to
 * the other windows. A change made in another window shows here at once when
 * the draft holds no edit; otherwise the edits stay, and `outdated` says why
 * the draft no longer starts from the saved answer ('elsewhere', or
 * 'regenerated' when a regeneration ended while editing).
 *
 * Mounted once per answer: moving to another one starts from a clean state.
 * `onLoaded(answer)`: the answer is loaded (a stable function).
 */
export const useAnswerWork = ({ answerId, onLoaded }) => {
  const confirm = useConfirm();
  const draft = useAnswerDraft();
  const history = useVersionHistory();
  const [answer, setAnswer] = useState(null);
  const [failed, setFailed] = useState(false);
  const [statusPending, setStatusPending] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [outdated, setOutdated] = useState(null);

  const { reset } = draft;
  const { fetchVersionHistory } = history;

  // Whether the draft holds edits, as of the latest render: read when a
  // request that took its time comes back.
  const changedRef = useRef(false);
  useEffect(() => {
    changedRef.current = draft.changed;
  });

  /** The answer the server sent, on screen; the draft starts from it unless `keepDraft`. */
  const show = useCallback(
    (data, { keepDraft = false } = {}) => {
      const next = withText(data);
      setAnswer(next);
      if (!keepDraft) {
        reset(next, parseSourcesFromString(next.sources));
        setOutdated(null);
      }
      return next;
    },
    [reset]
  );

  useEffect(() => {
    let cancelled = false;
    answersAPI
      .get(answerId)
      .then(response => {
        if (cancelled) return;
        const loaded = show(response.data);
        onLoaded?.(loaded);
        fetchVersionHistory(loaded.id);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [answerId, show, onLoaded, fetchVersionHistory]);

  const publish = () => publishAnswerChange({ sessionId: answer.session_id, answerId: answer.id });

  /** The answer fetched again. The draft follows, unless it holds edits and `reason` says why it does not. */
  const refetch = async reason => {
    try {
      const response = await answersAPI.get(answerId);
      const keepDraft = Boolean(reason) && changedRef.current;
      show(response.data, { keepDraft });
      if (keepDraft) setOutdated(reason);
      fetchVersionHistory(response.data.id);
    } catch {
      toast.error('Failed to reload the answer');
    }
  };

  // Another window changed this answer.
  useAnswerChanges(change => {
    if (answer && Number(change.answerId) === answer.id) refetch('elsewhere');
  });

  /** The saved answer, fetched again: the edits under way are dropped. */
  const reload = () => refetch(null);

  const discard = async () => {
    const confirmed = await confirm({
      title: 'Discard your changes',
      message: 'The text and the sources go back to the saved answer. Your changes are lost.',
      confirmLabel: 'Discard changes',
      danger: true,
    });
    if (confirmed && answer) show(answer);
  };

  const save = async () => {
    if (!answer) return;
    try {
      const { saved } = await draft.save(answer.id);
      publish();
      show(saved);
      fetchVersionHistory(answer.id);
      toast.success('Saved as a new version, to review.');
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to save the answer'));
    }
  };

  // The draft is left as it is: a status leaves the text alone.
  const toggleStatus = async () => {
    if (!answer) return;
    setStatusPending(true);
    try {
      const status = answer.status === 'approved' ? 'needs_review' : 'approved';
      const response = await answersAPI.updateStatus(answer.id, status);
      publish();
      show(response.data, { keepDraft: true });
    } catch {
      toast.error('Failed to update the answer status');
    } finally {
      setStatusPending(false);
    }
  };

  const revert = async (id, version) => {
    if (regenerating) {
      toast('Wait for the regeneration to end: it makes a new version too.');
      return;
    }
    if (draft.changed) {
      const confirmed = await confirm({
        title: 'Discard your changes',
        message: `Version ${version} replaces the text you are editing. Discard your unsaved changes and revert?`,
        confirmLabel: 'Discard and revert',
        danger: true,
      });
      if (!confirmed) return;
    }
    await history.revertToVersion(id, version, async () => {
      publish();
      const response = await answersAPI.get(id);
      show(response.data);
    });
  };

  // A synchronous request of 15 to 30 seconds: the window stays usable, and
  // an edit made meanwhile is kept. Resolves to false when it failed, for the
  // form to keep its fields.
  const regenerate = async guidance => {
    if (!answer) return false;
    setRegenerating(true);
    try {
      const response = await answersAPI.regenerate(answer.id, guidance);
      publish();
      const keepDraft = changedRef.current;
      show(response.data, { keepDraft });
      if (keepDraft) setOutdated('regenerated');
      fetchVersionHistory(answer.id);
      toast.success('Answer regenerated.');
      return true;
    } catch (error) {
      toast.error(errorMessage(error, 'Regeneration failed. Please try again.'));
      return false;
    } finally {
      setRegenerating(false);
    }
  };

  // Closing the window or leaving the application loses the edits, and a
  // regeneration under way would end unseen by the other windows.
  const holding = draft.changed || regenerating;
  useEffect(() => {
    if (!holding) return undefined;
    const warn = event => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [holding]);

  /** Before moving to another page of this window: true when it may. */
  const confirmLeave = async () => {
    if (draft.changed) {
      return confirm({
        title: 'Leave without saving',
        message: 'Your changes to this answer are not saved. Leave and lose them?',
        confirmLabel: 'Leave',
        danger: true,
      });
    }
    if (regenerating) {
      return confirm({
        title: 'Leave during the regeneration',
        message:
          'The answer is still being regenerated. The new answer will be saved, but this window will not show it. Leave anyway?',
        confirmLabel: 'Leave',
      });
    }
    return true;
  };

  return {
    answer,
    failed,
    draft,
    history,
    statusPending,
    regenerating,
    outdated,
    holding,
    save,
    toggleStatus,
    revert,
    regenerate,
    reload,
    discard,
    confirmLeave,
  };
};
