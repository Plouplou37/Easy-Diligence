import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { answersAPI } from '@/entities/answer';
import { buildQuestionnaire } from '../lib/questionnaire';

// The server's page size cap: a questionnaire has fewer questions, so one page
// holds a DD type's answers. Without it the server sends 100 and drops the rest.
const ALL_ANSWERS = 1000;

const NOTHING = { rows: [], sections: [], total: 0, done: 0 };

const fetchAnswers = async (sessionId, ddTypeCode) => {
  const response = await answersAPI.getBySession(sessionId, {
    limit: ALL_ANSWERS,
    dd_type: ddTypeCode,
  });
  return (response.data.answers || []).map(answer => ({ ...answer, text: answer.answer_text }));
};

/**
 * One questionnaire of a session under review: its questions, by section,
 * each with its current answer.
 *
 * `structure` (from useQuestionnaireStructures) gives every question, answered
 * or not; `structureReady` says whether it is known yet. `liveKey` changes with
 * the run's progress: a new value fetches the answers again, so the list fills
 * in while the run goes on. `reload` does the same behind the page, which
 * keeps what is selected and where it is.
 */
export const useQuestionnaireReview = ({
  sessionId,
  ddTypeCode,
  structure,
  structureReady,
  liveKey,
}) => {
  const [answers, setAnswers] = useState([]);
  const [answersLoading, setAnswersLoading] = useState(Boolean(ddTypeCode));
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!ddTypeCode) return undefined;
    let cancelled = false;
    setAnswersLoading(true);
    fetchAnswers(sessionId, ddTypeCode)
      .then(list => {
        if (cancelled) return;
        setAnswers(list);
        setFailed(false);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      })
      .finally(() => {
        if (!cancelled) setAnswersLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, ddTypeCode]);

  const reload = useCallback(
    async ({ silent = false } = {}) => {
      if (!ddTypeCode) return;
      try {
        setAnswers(await fetchAnswers(sessionId, ddTypeCode));
        setFailed(false);
      } catch {
        if (!silent) toast.error('Failed to reload the answers');
      }
    },
    [sessionId, ddTypeCode]
  );

  // The run moved on: its new answers are fetched. Silent: during a run, one
  // missed refresh is caught up by the next.
  const lastLiveKey = useRef(liveKey);
  useEffect(() => {
    if (lastLiveKey.current === liveKey) return;
    lastLiveKey.current = liveKey;
    reload({ silent: true });
  }, [liveKey, reload]);

  /** Changes made on the server already (an edit): kept on screen. */
  const patchAnswer = useCallback((answerId, changes) => {
    setAnswers(previous =>
      previous.map(answer => (answer.id === answerId ? { ...answer, ...changes } : answer))
    );
  }, []);

  /** A review status, stored, then shown. */
  const setStatus = useCallback(
    async (answerId, status) => {
      const response = await answersAPI.updateStatus(answerId, status);
      const saved = response.data || {};
      patchAnswer(answerId, {
        status: saved.status || status,
        editor_name: saved.editor_name,
        edited_at: saved.edited_at,
      });
    },
    [patchAnswer]
  );

  // Answers that could not be loaded are not "not answered": nothing is listed
  // until they are.
  const questionnaire = useMemo(
    () => (failed ? NOTHING : buildQuestionnaire(structure, answers)),
    [failed, structure, answers]
  );

  return {
    ...questionnaire,
    loading: answersLoading || !structureReady,
    failed,
    // Only the answered questions can be listed.
    structureMissing: structureReady && !structure,
    reload,
    patchAnswer,
    setStatus,
  };
};
