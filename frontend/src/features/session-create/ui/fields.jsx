import { field } from '@/shared/ui';

/**
 * A field's label with, on its right, what becomes of the value (AiBadge or
 * NotSentNote). Given to Input as its `label`; the field then takes
 * `aria-required` rather than `required`, whose own asterisk would wrap.
 */
export const FieldLabel = ({ text, required = false, badge }) => (
  <span className="flex items-center justify-between gap-2">
    <span>
      {text}
      {required && (
        <span aria-hidden="true" className="ml-1 text-theme-error">
          *
        </span>
      )}
    </span>
    {badge}
  </span>
);

/** A multi-line field, labelled like Input, with its help or its error. */
export const TextAreaField = ({ id, label, helper, error, className = '', ...props }) => {
  const note = error || helper ? `${id}-note` : undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-content">
        {label}
      </label>
      <textarea
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={note}
        className={`form-input block w-full resize-y px-3 py-2 text-sm ${error ? 'border-theme-error' : ''}`}
        {...props}
      />
      {error && (
        <p id={note} className={field.error}>
          {error}
        </p>
      )}
      {!error && helper && (
        <p id={note} className={field.help}>
          {helper}
        </p>
      )}
    </div>
  );
};

/** An inset block of a step: a title, what sits on its right, the content. */
export const InsetBlock = ({ title, aside, children, className = '' }) => (
  <div className={`form-surface flex flex-col gap-4 p-5 ${className}`}>
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="font-semibold text-content">{title}</h3>
      {aside}
    </div>
    {children}
  </div>
);

/** The error under a group of fields, which the group's `aria-describedby` names. */
export const FieldError = ({ id, children }) =>
  children ? (
    <p id={id} className={field.error}>
      {children}
    </p>
  ) : null;
