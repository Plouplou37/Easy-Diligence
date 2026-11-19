import { CheckCircleIcon, ClockIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { StatusBadge, panel, sectionHeader } from '@/shared/ui';

const BAR = {
  completed: 'bg-theme-success',
  in_progress: 'bg-gradient-to-r from-accent-blue to-accent-green',
};

/**
 * The session's overall progress. `stale`: the live updates stopped answering,
 * so the figures may be out of date.
 */
export const SessionProgressPanel = ({ overall, isRunning, stale }) => (
  <div className={panel.base}>
    <div className={`${panel.header} flex items-center justify-between gap-4`}>
      <div>
        <h2 className={sectionHeader.title}>Overall Progress</h2>
        <p className="text-sm text-content-secondary mt-1">
          Track the completion status of your due diligence analysis
        </p>
        {stale && (
          <p className="text-sm text-theme-warning mt-1 flex items-center gap-1.5">
            <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0" />
            Live updates interrupted — the figures below may be out of date.
          </p>
        )}
      </div>
      <StatusBadge status={overall.status} size="lg" className="flex-shrink-0 tabular-nums">
        {overall.completed} / {overall.total} Complete ({overall.percentage}%)
      </StatusBadge>
    </div>

    <div className={panel.body}>
      <div className="relative">
        <div className="w-full bg-surface-hover rounded-full h-2 overflow-hidden">
          <div
            className={`h-2 rounded-full transition-all duration-500 ease-out ${
              BAR[overall.status] || 'bg-content-muted/40'
            }`}
            style={{ width: `${overall.percentage}%` }}
          ></div>
        </div>
        <div className="flex justify-between text-xs text-content-muted tabular-nums mt-2">
          <span>0%</span>
          <span className="font-medium text-content">{overall.percentage}%</span>
          <span>100%</span>
        </div>
      </div>

      {overall.status === 'completed' && (
        <div className="mt-4 alert alert-success">
          <p className="text-sm flex items-center">
            <CheckCircleIcon className="w-5 h-5 mr-2 flex-shrink-0" />
            All due diligence types are complete.
          </p>
        </div>
      )}

      {isRunning && (
        <div className="mt-4 alert alert-info">
          <p className="text-sm flex items-center">
            <ClockIcon className="w-5 h-5 mr-2 flex-shrink-0 animate-pulse" />
            Processing in progress... Only one due diligence type can run at a time.
          </p>
        </div>
      )}
    </div>
  </div>
);
