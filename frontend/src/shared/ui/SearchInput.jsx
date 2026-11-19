import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';

/**
 * Search field with a magnifier and a clear button.
 * @param {Object} props
 * @param {string} props.value - Current text
 * @param {Function} props.onChange - Called with the new text (not the event)
 * @param {string} props.placeholder - Placeholder text
 * @param {string} props.className - Extra classes on the wrapper
 */
export const SearchInput = ({ value, onChange, placeholder = 'Search...', className = '', ...props }) => (
  <div className={`relative ${className}`}>
    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
      <MagnifyingGlassIcon className="h-4 w-4 text-content-muted" />
    </div>
    <input
      type="text"
      className="block w-full rounded-lg input-gradient-border pl-10 pr-9 py-2 text-sm text-content"
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      {...props}
    />
    {value && (
      <button
        type="button"
        onClick={() => onChange('')}
        className="absolute inset-y-0 right-0 pr-3 flex items-center text-content-muted hover:text-content"
        aria-label="Clear search"
      >
        <XMarkIcon className="h-4 w-4" />
      </button>
    )}
  </div>
);
