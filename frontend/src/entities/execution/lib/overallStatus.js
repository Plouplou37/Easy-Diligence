import { FINISHED_STATUSES, getSessionStatus } from './executionStatus';

/**
 * The state of a session across the DD types it shows: status, finished runs,
 * total, and the average progress.
 *
 * Only the DD types shown count: the progress holds every execution of the
 * session, including runs since deactivated or removed from it, and averaging
 * those over the smaller displayed count gave "3 / 2 Complete (150%)".
 */
export const getOverallStatus = (shownDdTypes, progressByCode) => {
  const total = shownDdTypes ? shownDdTypes.length : 0;
  if (!progressByCode || Object.keys(progressByCode).length === 0 || total === 0) {
    return { status: 'not_started', completed: 0, total, percentage: 0 };
  }
  const shown = new Set(shownDdTypes.map(ddType => ddType.code));
  const runs = Object.values(progressByCode).filter(run => !run.dd_type || shown.has(run.dd_type));
  const totalProgress = runs.reduce((sum, run) => sum + (run.percentage || 0), 0);
  return {
    status: getSessionStatus(runs, total),
    // Finished runs, not a percentage the progress endpoint rounds.
    completed: runs.filter(run => FINISHED_STATUSES.includes(run.status)).length,
    total,
    percentage: Math.min(Math.round(totalProgress / total), 100),
  };
};
