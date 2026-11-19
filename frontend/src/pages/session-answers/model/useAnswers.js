import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { answersAPI } from '@/entities/answer';
import { fetchDdTypes } from '@/entities/dd-type';
import { sessionAPI } from '@/entities/session';

// The server's page size cap: a questionnaire has fewer questions, so one page
// holds a DD type's answers. Without it the server sends 100 and drops the rest.
const ALL_ANSWERS = 1000;

/**
 * A session's answers for one DD type, with the session and the DD types.
 * `loading` covers the first load and a change of DD type; `reload` fetches the
 * answers again behind the page, which keeps what is open and where it is.
 */
export const useAnswers = (sessionId, ddTypeCode) => {
  const [session, setSession] = useState(null);
  const [ddTypes, setDdTypes] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAnswers = useCallback(async () => {
    const params = { limit: ALL_ANSWERS };
    if (ddTypeCode) params.dd_type = ddTypeCode;
    const response = await answersAPI.getBySession(sessionId, params);
    setAnswers(
      (response.data.answers || []).map(answer => ({ ...answer, text: answer.answer_text }))
    );
  }, [sessionId, ddTypeCode]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [sessionResponse, allDdTypes] = await Promise.all([
          sessionAPI.get(sessionId),
          // Inactive types too: their answers are still reviewed.
          fetchDdTypes({ activeOnly: false }),
          fetchAnswers(),
        ]);
        setSession(sessionResponse.data);
        setDdTypes(allDdTypes);
      } catch {
        toast.error('Failed to load session data');
        setAnswers([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [sessionId, fetchAnswers]);

  const reload = useCallback(async () => {
    try {
      await fetchAnswers();
    } catch {
      toast.error('Failed to reload the answers');
    }
  }, [fetchAnswers]);

  const updateAnswer = async (answerId, updates) => {
    let changes = updates;
    if (updates.status) {
      const response = await answersAPI.updateStatus(answerId, updates.status);
      changes = { status: response.data.status };
    }
    setAnswers(previous =>
      previous.map(answer => (answer.id === answerId ? { ...answer, ...changes } : answer))
    );
  };

  return { session, ddTypes, answers, loading, reload, updateAnswer };
};
