import { Link } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { DarkModeToggle } from '@/features/theme-toggle';

/**
 * The slim bar of the answer window, in place of the application's: where the
 * answer belongs (the due diligence, its fund, the questionnaire) and the way
 * to the due diligence. `onOpenDueDiligence`: the link's click, which may ask
 * before leaving.
 */
export const WindowHeader = ({ ddName, fund, questionnaire, ddUrl, onOpenDueDiligence }) => (
  <header className="sticky top-0 z-30 border-b border-border nav-bg">
    <div className="flex h-14 items-center gap-3 px-4 sm:px-6 lg:px-8">
      <span className="shrink-0 text-base font-bold tracking-tight whitespace-nowrap text-content">
        Easy Diligence
      </span>
      <span className="h-4 w-px shrink-0 bg-border" aria-hidden="true" />
      <p
        className="min-w-0 flex-1 truncate text-sm"
        title={[ddName, fund, questionnaire].filter(Boolean).join(' · ')}
      >
        <span className="font-medium text-content">{ddName}</span>
        {fund && <span className="text-content-muted"> · {fund}</span>}
        {questionnaire && <span className="text-content-secondary"> · {questionnaire}</span>}
      </p>
      <Link
        to={ddUrl}
        onClick={onOpenDueDiligence}
        title="Open the due diligence"
        className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-sm text-link transition-colors hover:bg-surface-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-blue"
      >
        <ArrowLeftIcon className="h-4 w-4 shrink-0" />
        <span className="max-sm:sr-only">Open the due diligence</span>
      </Link>
      <DarkModeToggle />
    </div>
  </header>
);
