import { StatTile } from '@/shared/ui';
import { plural } from '../lib/sessionRow';

/**
 * The figures that call for an action, calm: label, figure, a hint. The first
 * two also filter the list (a second click shows everything again).
 */
export const DashboardTiles = ({ totals, sessions, isLive, filters }) => {
  const withReview = sessions.filter(session => session.toReview > 0).length;
  const withSynthesis = sessions.filter(session =>
    session.dd_types.some(ddType => ddType.has_synthesis)
  ).length;
  const completed = sessions.filter(session => session.status === 'completed').length;
  const running = filters.status === 'in_progress';

  let reviewHint = 'Nothing to review';
  if (filters.reviewOnly) reviewHint = 'Filtering the list';
  else if (withReview) reviewHint = `In ${plural(withReview, 'due diligence')}`;

  let runningHint = 'Nothing running';
  if (running) runningHint = 'Filtering the list';
  else if (isLive) runningHint = 'Refreshing every 15 s';

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatTile
        label="Answers to review"
        value={totals.to_review || 0}
        hint={reviewHint}
        title={
          filters.reviewOnly
            ? 'Show every due diligence'
            : 'Show only the due diligences with answers to review'
        }
        onClick={() => filters.setReviewOnly(!filters.reviewOnly)}
        active={filters.reviewOnly}
      />
      <StatTile
        label="Running"
        value={totals.running || 0}
        hint={runningHint}
        title={running ? 'Show every due diligence' : 'Show only the due diligences in progress'}
        onClick={() => filters.setStatus(running ? 'all' : 'in_progress')}
        active={running}
      />
      <StatTile
        label="Syntheses ready"
        value={totals.syntheses_ready || 0}
        hint={withSynthesis ? `In ${plural(withSynthesis, 'due diligence')}` : 'None yet'}
      />
      <StatTile
        label="Due diligences"
        value={totals.sessions || 0}
        hint={`${completed} completed`}
      />
    </div>
  );
};
