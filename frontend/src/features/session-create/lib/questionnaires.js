// What a run costs, per question: measured orders of magnitude, not a quote.
export const SECONDS_PER_QUESTION = 15;
export const TOKENS_PER_QUESTION = 11_000;

/**
 * The DD types to choose from, each with its structure when known:
 * `sections` (from /questions/dd-types) and `counts` ({ sections, questions }),
 * both null when the structure could not be read. `ddTypes` carry the ids the
 * session is created with; `structures`, the sections and questions.
 */
export const mergeQuestionnaires = (ddTypes, structures) => {
  const byCode = new Map((structures || []).map(structure => [structure.code, structure]));
  return ddTypes.map(ddType => {
    const sections = byCode.get(ddType.code)?.sections || null;
    return {
      ...ddType,
      sections,
      counts: sections
        ? {
            sections: sections.length,
            questions: sections.reduce((total, section) => total + section.questions.length, 0),
          }
        : null,
    };
  });
};

/** The questions of the chosen questionnaires, or null when one count is unknown. */
export const questionCount = questionnaires =>
  questionnaires.every(questionnaire => questionnaire.counts)
    ? questionnaires.reduce((total, questionnaire) => total + questionnaire.counts.questions, 0)
    : null;

/** The run's time, roughly: "1 min", "45 min", "2 h 10 min". */
const aboutTime = seconds => {
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
};

/** The estimate of a run of `questions` questions, as shown; dashes when unknown. */
export const estimateRun = questions =>
  questions === null
    ? { questions: '—', time: '—', tokens: '—' }
    : {
        questions: questions.toLocaleString('en-US'),
        time: questions ? aboutTime(questions * SECONDS_PER_QUESTION) : '0 min',
        tokens: (questions * TOKENS_PER_QUESTION).toLocaleString('en-US'),
      };
