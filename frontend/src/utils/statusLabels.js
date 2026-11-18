/**
 * The label of every status, in one place. Each page used to carry its own
 * map, and they disagreed: "Partial" on a Dashboard badge but "Partially
 * Complete" in its filter, and "Unknown" in Answer Management for statuses the
 * DD cards named. Colours stay in utils/statusStyles.js.
 */

const LABELS = {
  // Sessions (derived, see utils/executionStatus.js) and executions
  not_started: 'Not Started',
  in_progress: 'In Progress',
  paused: 'Paused',
  partial: 'Partial',
  completed: 'Completed',
  failed: 'Failed',
  generated: 'Completed',
  under_review: 'Under Review',
  validated: 'Validated',
  finalized: 'Finalized',

  // Answers
  needs_review: 'Needs Review',
  approved: 'Approved',
  rejected: 'Rejected',
  draft: 'Draft',
  pending: 'Pending',
};

export const getStatusLabel = (status) => {
  const key = String(status || '').toLowerCase();
  if (LABELS[key]) return LABELS[key];
  // Unknown value: show it readably rather than "Unknown".
  return key ? key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()) : LABELS.not_started;
};

// Options for a session status filter, in the order a user scans them.
export const SESSION_STATUS_OPTIONS = [
  'not_started', 'in_progress', 'paused', 'partial', 'completed', 'failed',
].map((value) => ({ value, label: getStatusLabel(value) }));
