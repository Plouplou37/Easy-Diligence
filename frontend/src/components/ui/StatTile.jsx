import React from 'react';
import { panel } from './styles';

/**
 * Figure tile with the blue-to-green rail (Dashboard, Vector Stores).
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
export const StatTile = ({ label, value, hint, icon: Icon, iconClass = 'text-content-muted', title, onClick, active = false }) => {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      title={title}
      className={`${panel.base} overflow-hidden text-left w-full ${onClick ? 'transition-colors hover:border-bleu-atlantis/60' : ''} ${active ? 'border-bleu-atlantis' : ''}`}
    >
      <div className={panel.railBrand} />
      <div className="flex items-center gap-4 pl-6 pr-5 py-4">
        {Icon && <Icon className={`h-7 w-7 flex-shrink-0 ${iconClass}`} />}
        <dl className="min-w-0 flex-1">
          <dt className="eyebrow truncate">{label}</dt>
          <dd className="mt-1 text-fluid-xl font-light text-content tabular-nums truncate">{value}</dd>
          {hint && <dd className="mt-0.5 text-xs text-content-muted truncate">{hint}</dd>}
        </dl>
      </div>
    </Tag>
  );
};
