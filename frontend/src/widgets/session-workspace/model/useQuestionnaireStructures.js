import { useEffect, useMemo, useState } from 'react';
import { fetchDdTypes } from '@/entities/dd-type';

/**
 * The structure of every questionnaire the user can see (sections and
 * questions), in one cached request: the questions not answered yet are only
 * known from it. Inactive ones too: a session built on a since-deactivated
 * questionnaire still shows its questions.
 */
export const useQuestionnaireStructures = () => {
  const [structures, setStructures] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchDdTypes({ withQuestions: true, activeOnly: false })
      .then(list => {
        if (!cancelled) setStructures(Array.isArray(list) ? list : []);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return useMemo(() => {
    const byCode = new Map((structures || []).map(structure => [structure.code, structure]));
    const counts = {};
    byCode.forEach((structure, code) => {
      counts[code] = (structure.sections || []).reduce(
        (sum, section) => sum + (section.questions?.length || 0),
        0
      );
    });
    return {
      ready: structures !== null || failed,
      of: code => byCode.get(code) || null,
      // Number of questions of each questionnaire, by code.
      counts,
    };
  }, [structures, failed]);
};
