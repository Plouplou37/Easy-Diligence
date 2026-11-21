/**
 * Reusable Button component.
 * primary = blue contained (the one action of a screen), secondary =
 * outlined, ghost = text only, danger / success = contained in the matching
 * state colour.
 * Without children (icon only) it takes the compact icon-button look.
 * @param {Object} props
 * @param {'primary'|'secondary'|'danger'|'success'|'ghost'} props.variant - Button style variant
 * @param {'sm'|'md'|'lg'} props.size - Button size
 * @param {React.ComponentType} props.icon - Optional icon component (from heroicons)
 * @param {boolean} props.loading - Show loading spinner
 * @param {boolean} props.disabled - Disabled state
 * @param {React.ReactNode} props.children - Button content
 */
export const Button = ({
  variant = 'primary',
  size = 'md',
  icon: Icon,
  loading = false,
  disabled = false,
  className = '',
  children,
  ...props
}) => {
  const iconOnly = !children;

  // The press shows at once (pointer down, not release): a slight scale-down,
  // left out when the system asks for reduced motion.
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg whitespace-nowrap transition duration-150 ease-out motion-safe:active:scale-[0.97] focus:outline-hidden focus-visible:ring-2 focus-visible:ring-accent-blue/60 focus-visible:ring-offset-1 focus-visible:ring-offset-surface disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-primary text-white font-semibold hover:bg-primary/90',
    secondary:
      'border border-border-hover bg-transparent text-content hover:bg-surface-hover hover:border-content-muted',
    danger: 'bg-theme-error text-content-inverse font-semibold hover:bg-theme-error/90',
    success: 'bg-theme-success text-content-inverse font-semibold hover:bg-theme-success/90',
    ghost: 'text-content-secondary hover:text-content hover:bg-surface-hover',
  };

  const iconOnlyVariants = {
    primary: 'text-content hover:bg-surface-hover',
    secondary: 'text-content-secondary hover:text-content hover:bg-surface-hover',
    danger: 'text-theme-error hover:bg-theme-error-bg',
    success: 'text-theme-success hover:bg-theme-success-bg',
    ghost: 'text-content-secondary hover:text-content hover:bg-surface-hover',
  };

  const sizes = {
    sm: 'h-8 px-3 text-xs gap-1.5',
    md: 'h-10 px-4 text-sm gap-2',
    lg: 'h-11 px-5 text-sm gap-2',
  };

  const iconOnlySizes = {
    sm: 'p-1.5',
    md: 'p-2',
    lg: 'p-2.5',
  };

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  const variantStyles = iconOnly
    ? iconOnlyVariants[variant] || iconOnlyVariants.ghost
    : variants[variant] || variants.primary;
  const sizeStyles = iconOnly ? iconOnlySizes[size] || iconOnlySizes.md : sizes[size] || sizes.md;
  const isDisabled = disabled || loading;

  return (
    <button
      className={`${baseStyles} ${variantStyles} ${sizeStyles} ${className}`}
      disabled={isDisabled}
      {...props}
    >
      {loading && (
        <svg
          className={`animate-spin ${iconSizes[size] || iconSizes.md}`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      )}
      {!loading && Icon && <Icon className={`${iconSizes[size] || iconSizes.md} shrink-0`} />}
      {children}
    </button>
  );
};
