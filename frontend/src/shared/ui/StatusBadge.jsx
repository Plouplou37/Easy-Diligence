import {
  CheckCircleIcon,
  ClockIcon,
  EyeIcon,
  PauseIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { Badge } from './Badge';
import { getStatusTone } from '@/shared/lib/status';
import { getStatusLabel } from '@/shared/lib/status';

const ICONS = {
  in_progress: cls => <ClockIcon className={`${cls} animate-pulse`} />,
  paused: cls => <PauseIcon className={cls} />,
  failed: cls => <XCircleIcon className={cls} />,
  completed: cls => <CheckCircleIcon className={cls} />,
  generated: cls => <CheckCircleIcon className={cls} />,
  validated: cls => <CheckCircleIcon className={cls} />,
  finalized: cls => <CheckCircleIcon className={cls} />,
  approved: cls => <CheckCircleIcon className={cls} />,
  under_review: cls => <EyeIcon className={cls} />,
};

/**
 * Status chip: shared label (utils/statusLabels) and tone (utils/statusStyles).
 * @param {Object} props
 * @param {string} props.status - Session, execution or answer status
 * @param {'sm'|'md'|'lg'} props.size - Badge size
 * @param {boolean} props.showIcon - Show the status icon (default true)
 * @param {React.ReactNode} props.children - Replaces the label (same colour)
 */
export const StatusBadge = ({ status, size = 'md', showIcon = true, className = '', children }) => {
  const key = String(status || 'not_started').toLowerCase();
  const icon = showIcon && ICONS[key] ? ICONS[key](size === 'lg' ? 'w-4 h-4' : 'w-3 h-3') : null;
  return (
    <Badge variant={getStatusTone(key)} size={size} className={className}>
      {icon}
      <span>{children || getStatusLabel(key)}</span>
    </Badge>
  );
};
