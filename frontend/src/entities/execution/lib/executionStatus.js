// Execution statuses that mean a DD run is over. The session status endpoint
// maps `generated` to 'completed' but passes under_review / validated /
// finalized through untouched: treating only 'completed' as finished made a
// validated DD look unstarted on its card ("Not Started", a Start button, no
// analytics) and a validated session look only partly done on the Dashboard.
export const FINISHED_STATUSES = ['completed', 'under_review', 'validated', 'finalized'];

// Session statuses counted as "In Progress": started but not finished. A
// session with one DD type done and another still to run is `partial`, and it
// is as much in progress as one whose run is executing right now.
export const IN_PROGRESS_STATUSES = ['in_progress', 'partial', 'paused'];

/**
 * Status of a session, derived from the progress of its DD types.
 *
 * The one rule for every screen. The Dashboard and the session page each had
 * their own (the latter knew neither `paused` nor `partial`, and judged "done"
 * on a percentage), so one session could read "Partial" on the first and
 * "In Progress" on the second. A session has no status of its own in the
 * backend: its state is that of its runs, and the deletion guard
 * (services/sessions.py) reads them by the same rule.
 *
 * @param {Array<{status: string}>} progressList - Progress of the DD types shown for the session
 * @param {number} totalConfigured - Number of DD types configured on the session
 */
export const getSessionStatus = (progressList, totalConfigured) => {
  if (!totalConfigured || !progressList || progressList.length === 0) return 'not_started';

  const statuses = progressList.map(p => p.status);
  const finished = statuses.filter(s => FINISHED_STATUSES.includes(s)).length;

  if (finished >= totalConfigured) return 'completed';
  if (statuses.includes('in_progress')) return 'in_progress';
  if (statuses.includes('paused')) return 'paused';
  if (statuses.includes('failed')) return 'failed';
  if (finished > 0) return 'partial';
  return 'not_started';
};

/**
 * Average completion percentage over the configured DD types (0-100).
 * A DD type with no progress yet counts as 0.
 */
export const getSessionProgress = (progressList, totalConfigured) => {
  if (!totalConfigured || !progressList || progressList.length === 0) return 0;
  const sum = progressList.reduce((acc, p) => acc + (p.percentage || 0), 0);
  return Math.min(Math.round(sum / totalConfigured), 100);
};
