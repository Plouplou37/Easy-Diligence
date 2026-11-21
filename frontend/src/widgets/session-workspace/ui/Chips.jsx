import { Badge } from '@/shared/ui';
import { STATES } from '../lib/questionnaire';

/** Where a question stands: approved, to review, not answered, failed. */
export const StateChip = ({ state }) => {
  const { label, tone } = STATES[state] || STATES.none;
  return (
    <Badge variant={tone} size="sm">
      {label}
    </Badge>
  );
};

/** A thin bar: `percentage` filled, in `fill` (a background class). */
export const ThinBar = ({ percentage, fill = 'bg-primary', className = '' }) => (
  <span className={`block h-1 w-full overflow-hidden rounded-full bg-surface-hover ${className}`}>
    <span
      className={`block h-full rounded-full transition-[width] duration-300 ${fill}`}
      style={{ width: `${Math.max(0, Math.min(100, percentage))}%` }}
    />
  </span>
);
