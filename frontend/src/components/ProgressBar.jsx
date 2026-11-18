import React from 'react';
import { CheckIcon, ClockIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { getStatusStyles } from '../utils/statusStyles';

const ProgressBar = ({
  current,
  total,
  status,
  label = "Progress",
  showDetails = true,
  size = "md"
}) => {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
  const tone = getStatusStyles(status);

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckIcon className="w-4 h-4 text-theme-success" />;
      case 'in_progress':
        return <ClockIcon className="w-4 h-4 text-accent-blue animate-spin" />;
      case 'failed':
        return <ExclamationTriangleIcon className="w-4 h-4 text-theme-error" />;
      case 'paused':
        return <ClockIcon className="w-4 h-4 text-theme-warning" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'in_progress':
        return 'In Progress';
      case 'failed':
        return 'Failed';
      case 'paused':
        return 'Paused';
      case 'not_started':
        return 'Not Started';
      default:
        return 'Unknown';
    }
  };

  const heightClass = size === 'sm' ? 'h-1.5' : size === 'lg' ? 'h-3' : 'h-2';

  return (
    <div className="w-full">
      {showDetails && (
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-content-secondary">{label}</span>
            {getStatusIcon()}
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-sm text-content-muted tabular-nums">
              {current} / {total}
            </span>
            <span className="text-sm font-medium text-content tabular-nums">
              {percentage}%
            </span>
          </div>
        </div>
      )}

      {/* Progress bar */}
      <div className="w-full bg-surface-hover rounded-full overflow-hidden">
        <div
          className={`${heightClass} ${tone.fill} transition-all duration-300 ease-out rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {showDetails && (
        <div className="flex items-center justify-between mt-1">
          <span className={`text-xs ${
            status === 'failed' ? 'text-theme-error' :
            status === 'completed' ? 'text-theme-success' :
            'text-content-muted'
          }`}>
            {getStatusText()}
          </span>
          {percentage === 100 && status === 'completed' && (
            <span className="text-xs text-theme-success font-medium">
               Complete
            </span>
          )}
        </div>
      )}
    </div>
  );
};

// Mini progress bar component for compact displays
export const MiniProgressBar = ({ current, total, status }) => {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
  const tone = getStatusStyles(status);

  return (
    <div className="flex items-center space-x-2">
      <div className="flex-1 bg-surface-hover rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-1.5 ${tone.fill} transition-all duration-300 ease-out rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-content-muted tabular-nums min-w-[3rem]">
        {percentage}%
      </span>
    </div>
  );
};

export default ProgressBar;
