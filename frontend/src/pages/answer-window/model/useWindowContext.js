import { useEffect, useState } from 'react';
import { answersAPI } from '@/entities/answer';
import { fetchDdTypes } from '@/entities/dd-type';
import { sessionAPI } from '@/entities/session';
import { buildQuestionnaire } from '@/widgets/session-workspace';

// The server's page size cap, as in the workspace: one page holds every
// answer of a questionnaire.
const ALL_ANSWERS = 1000;

/** The due diligence, for the window's header. Null until known, or if it cannot be. */
export const useSession = sessionId => {
  const [session, setSession] = useState(null);

  useEffect(() => {
    let cancelled = false;
    sessionAPI
      .get(sessionId)
      .then(response => {
        if (!cancelled) setSession(response.data);
      })
      // The answer carries the session's name: the header does without.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  return session;
};

/**
 * The answers of one questionnaire of the session, in the order of the
 * workspace (its sections and questions), for Previous and Next: `ids`, the
 * answer ids in that order; `ddType`, the questionnaire with its structure
 * (null when it could not be loaded: the answers then follow their sections
 * as the server lists them, as in the workspace).
 */
export const useQuestionnaireOrder = (sessionId, ddTypeCode) => {
  const [order, setOrder] = useState({ ids: [], ddType: null });

  useEffect(() => {
    if (!ddTypeCode) return undefined;
    let cancelled = false;
    Promise.all([
      answersAPI.getBySession(sessionId, { dd_type: ddTypeCode, limit: ALL_ANSWERS }),
      // The same cached request as the workspace's.
      fetchDdTypes({ withQuestions: true, activeOnly: false }).catch(() => null),
    ])
      .then(([response, structures]) => {
        if (cancelled) return;
        const answers = (response.data.answers || []).map(answer => ({
          ...answer,
          text: answer.answer_text,
        }));
        const ddType = Array.isArray(structures)
          ? structures.find(structure => structure.code === ddTypeCode) || null
          : null;
        const { rows } = buildQuestionnaire(ddType, answers);
        setOrder({ ids: rows.filter(row => row.answer).map(row => row.answer.id), ddType });
      })
      // Without the list, Previous and Next stay disabled: the answer is still there.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId, ddTypeCode]);

  return order;
};
