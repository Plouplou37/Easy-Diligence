import { CheckIcon } from '@heroicons/react/16/solid';

/**
 * The steps of the flow, numbered: done, current or upcoming. Each one opens
 * on a click; `onPick(n)` decides whether the steps before it allow it.
 * `steps`: [{ label, hint }]. `reached`: the furthest step opened so far.
 */
export const StepList = ({ steps, current, reached, onPick, note }) => (
  <>
    <ol className="flex flex-col gap-1">
      {steps.map((item, index) => {
        const number = index + 1;
        const isCurrent = number === current;
        const done = !isCurrent && number < reached;

        let circle = 'bg-surface-hover text-content-secondary';
        if (isCurrent) circle = 'bg-primary text-white';
        else if (done) circle = 'bg-theme-success-bg text-theme-success';

        let label = 'font-medium text-content-secondary';
        if (isCurrent) label = 'font-semibold text-content';
        else if (done) label = 'font-medium text-content';

        return (
          <li key={item.label}>
            <button
              type="button"
              onClick={() => onPick(number)}
              aria-current={isCurrent ? 'step' : undefined}
              className={`flex w-full min-h-11 items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors focus:outline-hidden focus-visible:ring-2 focus-visible:ring-accent-blue/60 ${
                isCurrent
                  ? 'border-primary bg-primary-dark'
                  : 'border-transparent hover:bg-surface-hover'
              }`}
            >
              <span
                aria-hidden="true"
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[0.8125rem] font-semibold tabular-nums ${circle}`}
              >
                {done ? <CheckIcon className="h-4 w-4" /> : number}
              </span>
              <span className="flex min-w-0 flex-col">
                <span className={`text-sm ${label}`}>
                  <span className="sr-only">Step {number}: </span>
                  {item.label}
                  {done && <span className="sr-only"> (done)</span>}
                </span>
                <span className="text-xs text-content-muted">{item.hint}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ol>
    {note && <p className="mt-5 px-1 text-xs text-content-muted">{note}</p>}
  </>
);
