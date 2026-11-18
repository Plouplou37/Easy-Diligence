import React from 'react';

/**
 * Reusable Input component with integrated label and validation (text field look:
 * the border fills with the blue-to-green gradient on focus)
 * @param {Object} props
 * @param {string} props.label - Input label text
 * @param {string} props.error - Error message to display
 * @param {string} props.helperText - Helper text below input
 * @param {React.ComponentType} props.leftIcon - Optional left icon component
 * @param {React.ComponentType} props.rightIcon - Optional right icon component
 * @param {string} props.type - Input type (text, email, password, number, etc.)
 * @param {boolean} props.required - Required field indicator
 * @param {boolean} props.disabled - Disabled state
 * @param {string} props.placeholder - Placeholder text
 */
export const Input = ({
  label,
  error,
  helperText,
  leftIcon: LeftIcon,
  rightIcon: RightIcon,
  type = 'text',
  required = false,
  disabled = false,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const hasError = !!error;

  const baseInputStyles = 'block w-full rounded-lg py-2 text-sm text-content transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

  // The gradient border needs its own transparent border, so the error state
  // switches to the plain field recipe instead of adding a border colour.
  const inputStyles = hasError
    ? 'form-input border-theme-error'
    : 'input-gradient-border';

  const paddingStyles = LeftIcon && RightIcon
    ? 'pl-10 pr-10'
    : LeftIcon
    ? 'pl-10 pr-3'
    : RightIcon
    ? 'pl-3 pr-10'
    : 'px-3';

  return (
    <div className={className}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-xs font-medium text-content-secondary mb-1"
        >
          {label}
          {required && <span className="text-theme-error ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        {LeftIcon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LeftIcon className="h-4 w-4 text-content-muted" />
          </div>
        )}

        <input
          id={inputId}
          type={type}
          disabled={disabled}
          className={`${baseInputStyles} ${inputStyles} ${paddingStyles}`}
          {...props}
        />

        {RightIcon && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <RightIcon className="h-4 w-4 text-content-muted" />
          </div>
        )}
      </div>

      {error && (
        <p className="mt-1 text-xs text-theme-error">
          {error}
        </p>
      )}

      {!error && helperText && (
        <p className="mt-1 text-xs text-content-muted">
          {helperText}
        </p>
      )}
    </div>
  );
};
