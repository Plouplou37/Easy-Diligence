import {
  ClockIcon,
  DocumentTextIcon,
  PencilSquareIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { StatTile } from '@/shared/ui';

/** What calls for an action; the first two tiles also filter the table. */
export const DashboardTiles = ({ totals, sessions, isLive, filters }) => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <StatTile
      label="Answers to review"
      value={totals.to_review || 0}
      hint={filters.reviewOnly ? 'Showing sessions with answers to review' : 'Not approved yet'}
      icon={PencilSquareIcon}
      iconClass="text-theme-warning"
      onClick={() => filters.setReviewOnly(!filters.reviewOnly)}
      active={filters.reviewOnly}
    />
    <StatTile
      label="Running"
      value={totals.running || 0}
      hint={isLive ? 'Refreshing every 15 s' : 'Nothing running'}
      icon={ClockIcon}
      iconClass="text-accent-blue"
      onClick={() => filters.setStatus(filters.status === 'in_progress' ? 'all' : 'in_progress')}
      active={filters.status === 'in_progress'}
    />
    <StatTile
      label="Syntheses ready"
      value={totals.syntheses_ready || 0}
      icon={SparklesIcon}
      iconClass="text-accent-gold"
    />
    <StatTile
      label="Sessions"
      value={totals.sessions || 0}
      hint={`${sessions.filter(session => session.status === 'completed').length} completed`}
      icon={DocumentTextIcon}
    />
  </div>
);
