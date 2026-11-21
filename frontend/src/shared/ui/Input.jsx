import { useId, useState } from 'react';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

/**
 * A text field with its label, help and error (the border fills with the
 * blue-to-green gradient on focus).
 * @param {Object} props
 * @param {string} props.label - Input label text
 * @param {string} props.error - Error message to display
 * @param {string} props.helperText - Helper text below input
 * @param {React.ComponentType} props.leftIcon - Optional left icon component
 * @param {React.ComponentType} props.rightIcon - Optional right icon component
 * @param {React.ReactNode} props.rightSlot - Optional control at the right end (clickable)
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
  rightSlot,
  type = 'text',
  required = false,
  disabled = false,
  className = '',
  id,
  ...props
}) => {
  // Stable across renders: a random id changed on every keystroke.
  const generatedId = useId();
  const inputId = id || generatedId;
  const hasError = Boolean(error);
  const hasRight = Boolean(RightIcon || rightSlot);

  const baseInputStyles =
    'block w-full rounded-lg h-10 py-2 text-sm text-content transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

  const inputStyles = hasError ? 'form-input border-theme-error' : 'input-gradient-border';
  const paddingStyles = `${LeftIcon ? 'pl-10' : 'pl-3'} ${hasRight ? 'pr-10' : 'pr-3'}`;

  return (
    <div className={className}>
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-content mb-1.5">
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
          required={required}
          disabled={disabled}
          aria-invalid={hasError || undefined}
          aria-describedby={error || helperText ? `${inputId}-note` : undefined}
          className={`${baseInputStyles} ${inputStyles} ${paddingStyles}`}
          {...props}
        />

        {rightSlot ? (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">{rightSlot}</div>
        ) : (
          RightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <RightIcon className="h-4 w-4 text-content-muted" />
            </div>
          )
        )}
      </div>

      {error && (
        <p id={`${inputId}-note`} className="mt-1 text-xs text-theme-error">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p id={`${inputId}-note`} className="mt-1 text-xs text-content-muted">
          {helperText}
        </p>
      )}
    </div>
  );
};

/** A password field whose content can be shown. */
export const PasswordInput = props => {
  const [shown, setShown] = useState(false);
  return (
    <Input
      {...props}
      type={shown ? 'text' : 'password'}
      rightSlot={
        <button
          type="button"
          onClick={() => setShown(!shown)}
          className="text-content-muted hover:text-content transition-colors"
          aria-label={shown ? 'Hide password' : 'Show password'}
          aria-pressed={shown}
        >
          {shown ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
        </button>
      }
    />
  );
};
