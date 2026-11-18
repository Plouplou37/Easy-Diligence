import React from 'react';

/**
 * Reusable Card component — panel on the wave background, uppercase section
 * title followed by a gradient hairline.
 * @param {Object} props
 * @param {string} props.title - Optional card title
 * @param {string} props.description - Optional card description
 * @param {React.ReactNode} props.children - Card body content
 * @param {React.ReactNode} props.actions - Optional actions/footer content
 * @param {boolean} props.noPadding - Remove default padding from body
 * @param {string} props.className - Additional CSS classes
 */
export const Card = ({
  title,
  description,
  children,
  actions,
  noPadding = false,
  className = '',
}) => {
  return (
    <div className={`relative bg-surface border border-border rounded-lg shadow-sm ${className}`}>
      {(title || description) && (
        <div className="px-5 py-3.5 border-b border-border">
          {title && (
            <div className="flex items-center gap-3">
              <h3 className="flex items-center gap-2 text-fluid-sm font-medium text-content uppercase tracking-[0.18em] whitespace-nowrap">
                {title}
              </h3>
              <div className="flex-1 h-px hairline-gradient opacity-40" />
            </div>
          )}
          {description && (
            <p className="text-sm text-content-secondary mt-1">
              {description}
            </p>
          )}
        </div>
      )}
      <div className={noPadding ? '' : 'p-5'}>
        {children}
      </div>
      {actions && (
        <div className="px-5 py-3 bg-surface-bg border-t border-border rounded-b-lg">
          {actions}
        </div>
      )}
    </div>
  );
};
