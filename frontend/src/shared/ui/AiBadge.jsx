import { SparklesIcon } from '@heroicons/react/24/outline';

/**
 * Marks what concerns the AI: a field the model reads ("Sent to the AI"),
 * documents it searches. Violet, the colour kept for the AI alone.
 */
export const AiBadge = ({ children = 'Sent to the AI', title, className = '' }) => (
  <span
    title={title}
    className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border border-theme-ai-border bg-theme-ai-bg px-2 py-0.5 text-[0.6875rem] font-semibold leading-4 text-theme-ai ${className}`}
  >
    <SparklesIcon className="h-3 w-3 shrink-0" aria-hidden="true" />
    {children}
  </span>
);
