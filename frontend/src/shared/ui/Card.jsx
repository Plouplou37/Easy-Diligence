/**
 * Reusable Card component — a bordered surface, with an optional title and
 * description in its header.
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
    <div className={`relative bg-surface border border-border rounded-xl ${className}`}>
      {(title || description) && (
        <div className="px-5 py-4 border-b border-border">
          {title && (
            <h3 className="flex items-center gap-2 text-base font-semibold text-content">
              {title}
            </h3>
          )}
          {description && <p className="text-sm text-content-secondary mt-1">{description}</p>}
        </div>
      )}
      <div className={noPadding ? '' : 'p-5'}>{children}</div>
      {actions && (
        <div className="px-5 py-3 bg-surface-bg border-t border-border rounded-b-xl">{actions}</div>
      )}
    </div>
  );
};
