import React from 'react';

/**
 * Reusable Button component.
 * primary = navy contained, secondary = outlined, ghost = text only,
 * danger / success = contained in the matching state colour.
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

  const baseStyles = 'inline-flex items-center justify-center font-normal rounded-md transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-primary-dark text-white hover:bg-primary-dark/85',
    secondary: 'border border-primary/30 bg-surface text-content hover:border-bleu-atlantis/80 hover:text-bleu-atlantis',
    danger: 'bg-theme-error text-content-inverse hover:bg-theme-error/85',
    success: 'bg-theme-success text-content-inverse hover:bg-theme-success/85',
    ghost: 'text-content hover:bg-primary/5',
  };

  const iconOnlyVariants = {
    primary: 'text-content hover:bg-primary/10',
    secondary: 'text-content-secondary hover:text-content hover:bg-surface-hover',
    danger: 'text-theme-error hover:bg-theme-error-bg',
    success: 'text-theme-success hover:bg-theme-success-bg',
    ghost: 'text-content-secondary hover:text-content hover:bg-surface-hover',
  };

  const sizes = {
    sm: 'px-2.5 py-1 text-xs gap-1.5',
    md: 'px-3 py-1.5 text-sm gap-1.5',
    lg: 'px-4 py-2 text-sm gap-2',
  };

  const iconOnlySizes = {
    sm: 'p-1',
    md: 'p-1.5',
    lg: 'p-2',
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
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      )}
      {!loading && Icon && <Icon className={`${iconSizes[size] || iconSizes.md} flex-shrink-0`} />}
      {children}
    </button>
  );
};
