const ROLES = {
  admin: { label: 'Admin', variant: 'info' },
  analyst: { label: 'Analyst', variant: 'neutral' },
};

/** A role's label and its badge variant (shared/ui Badge). */
export const roleOf = role =>
  ROLES[role] || {
    label: role ? role.replace(/^\w/, c => c.toUpperCase()) : '—',
    variant: 'neutral',
  };

/** The account's initials: from its full name, else its username. */
export const initialsOf = user =>
  (user?.full_name || user?.username || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0].toUpperCase())
    .join('') || '?';

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
