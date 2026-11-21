/**
 * A field's label, with a note on the right: what the AI reads of the field
 * (an AiBadge), or that it never does.
 */
export const FieldLabel = ({ htmlFor, required = false, aside, children }) => (
  <div className="mb-1.5 flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
    <label htmlFor={htmlFor} className="text-sm font-medium text-content">
      {children}
      {required && (
        <span className="ml-1 text-theme-error" aria-hidden="true">
          *
        </span>
      )}
    </label>
    {aside}
  </div>
);
