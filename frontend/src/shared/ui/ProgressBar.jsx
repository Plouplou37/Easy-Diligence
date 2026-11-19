import { getStatusStyles } from '@/shared/lib/status';

/** A thin progress bar with its percentage, in the colour of `status`. */
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
      <span className="text-xs text-content-muted tabular-nums min-w-[3rem]">{percentage}%</span>
    </div>
  );
};
