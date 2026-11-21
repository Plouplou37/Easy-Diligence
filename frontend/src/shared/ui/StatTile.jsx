import { panel } from './styles';

/**
 * Figure tile (Dashboard, Vector Stores).
 * @param {Object} props
 * @param {string} props.label - Small-caps label
 * @param {React.ReactNode} props.value - The figure
 * @param {React.ReactNode} props.hint - Optional line under the figure
 * @param {React.ComponentType} props.icon - Optional heroicon
 * @param {string} props.iconClass - Colour class of the icon
 * @param {string} props.title - Optional tooltip (technical detail kept out of sight)
 * @param {Function} props.onClick - Makes the tile a button (e.g. apply a filter)
 * @param {boolean} props.active - Highlights a clickable tile
 */
export const StatTile = ({
  label,
  value,
  hint,
  icon: Icon,
  iconClass = 'text-content-muted',
  title,
  onClick,
  active = false,
}) => {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      title={title}
      className={`${panel.base} overflow-hidden text-left w-full ${onClick ? 'transition duration-150 ease-out hover:border-border-hover motion-safe:active:scale-[0.98]' : ''} ${active ? 'border-primary bg-primary-dark' : ''}`}
    >
      <div className="flex items-center gap-4 px-5 py-4">
        {Icon && <Icon className={`h-6 w-6 shrink-0 ${iconClass}`} />}
        <dl className="min-w-0 flex-1">
          <dt className="eyebrow truncate">{label}</dt>
          <dd className="mt-1 text-2xl font-semibold tracking-tight text-content tabular-nums truncate">
            {value}
          </dd>
          {hint && <dd className="mt-0.5 text-xs text-content-muted truncate">{hint}</dd>}
        </dl>
      </div>
    </Tag>
  );
};
