import { getToneStyles } from '@/shared/lib/status';

const ROLE_TONES = { admin: 'brand', analyst: 'info' };

/** The badge classes of a role. */
export const roleBadge = role => getToneStyles(ROLE_TONES[role] || 'neutral').badge;

/** A login or creation date, with its time; "Never" when there is none. */
export const formatUserDate = value =>
  value
    ? new Date(value).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Never';
