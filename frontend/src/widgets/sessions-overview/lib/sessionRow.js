// A run whose last answer is older than this has probably stopped (server
// restarted mid-run): the execution stays `in_progress` with nothing behind it.
export const STALLED_AFTER_MS = 10 * 60 * 1000;

/** "1 due diligence", "3 due diligences". */
export const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`;

/** Questions answered in a DD type, never more than it has (questions since deleted). */
export const answeredOf = ddType => Math.min(ddType.answered || 0, ddType.total_questions || 0);

export const sessionUrl = session => `/session/${session.session_code || session.id}`;

/** The answers of one DD type of the session, or another tab of that page (`synthesis`). */
export const answersUrl = (session, ddType, tab) =>
  `${sessionUrl(session)}/answers?dd_type=${ddType.code}${tab ? `&tab=${tab}` : ''}`;

/** The DD types of the session whose run looks stopped: running, no new answer for a while. */
export const stalledRuns = (session, now = Date.now()) =>
  session.dd_types.filter(
    ddType =>
      ddType.status === 'in_progress' &&
      ddType.last_answer_at &&
      now - new Date(ddType.last_answer_at).getTime() > STALLED_AFTER_MS
  );
