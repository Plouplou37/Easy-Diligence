/**
 * A radio button or a checkbox shown as a card: a real input and its label,
 * so the keyboard and screen readers treat it as one. `aside` sits on the
 * right (a count, a badge), and goes under the text when space runs out.
 */
export const ChoiceCard = ({
  id,
  type = 'radio',
  name,
  checked,
  onChange,
  disabled = false,
  title,
  hint,
  aside,
  className = '',
}) => {
  let look = 'border-border bg-surface-bg hover:border-border-hover cursor-pointer';
  if (checked) look = 'border-primary bg-primary-dark cursor-pointer';
  if (disabled) look = 'border-border bg-surface-bg cursor-not-allowed opacity-50';

  return (
    <label
      htmlFor={id}
      className={`flex flex-wrap items-start gap-x-3 gap-y-1 rounded-xl border px-4 py-3.5 transition-colors has-focus-visible:ring-2 has-focus-visible:ring-accent-blue/60 ${look} ${className}`}
    >
      <input
        id={id}
        type={type}
        name={name}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="mt-0.5 h-4 w-4 shrink-0 focus:outline-hidden"
      />
      <span className="flex min-w-0 flex-[1_1_12rem] flex-col gap-0.5">
        <span className="text-sm font-semibold text-content break-words">{title}</span>
        {hint && (
          <span
            className="text-xs text-content-secondary line-clamp-2"
            title={typeof hint === 'string' ? hint : undefined}
          >
            {hint}
          </span>
        )}
      </span>
      {aside && <span className="ml-auto shrink-0">{aside}</span>}
    </label>
  );
};
