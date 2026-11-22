import { forwardRef, useState } from 'react';
import toast from 'react-hot-toast';
import {
  ArrowTopRightOnSquareIcon,
  ArrowUpIcon,
  CursorArrowRaysIcon,
} from '@heroicons/react/24/outline';
import { AnswerPanel } from '@/features/answer-review';
import { EmptyState } from '@/shared/ui';
import { versionNote } from '../lib/questionnaire';
import { FOCUS_RING } from '../lib/focus';
import { StateChip } from './Chips';

// The answer windows opened from this page, by window name. Clicking again
// brings the window to the front rather than loading it again, which would
// drop an edit under way.
const answerWindows = new Map();

const isPlainClick = event =>
  event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;

/**
 * Opens the answer in a window of its own. A link: a middle click or a
 * modified click (Ctrl, Shift, ⌘) opens it in a tab, as the browser does.
 */
const OpenInWindow = ({ href, answerId }) => {
  const open = event => {
    if (!isPlainClick(event)) return;
    event.preventDefault();
    const name = `answer-${answerId}`;
    const existing = answerWindows.get(name);
    if (existing && !existing.closed && existing.location.pathname === href) {
      existing.focus();
      return;
    }
    const opened = window.open(href, name, 'popup,width=1280,height=900');
    if (!opened) {
      toast.error('The browser blocked the window: allow pop-ups for this site, or Ctrl-click.');
      return;
    }
    answerWindows.set(name, opened);
    opened.focus();
  };

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={open}
      aria-label="Open in a new window"
      title="Open in a new window"
      className={`-my-2 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-content-secondary transition-colors hover:bg-surface-hover hover:text-content ${FOCUS_RING}`}
    >
      <ArrowTopRightOnSquareIcon className="h-5 w-5" />
    </a>
  );
};

// The views of a question. One today; what was sent to the AI and an assistant
// are to come, as tabs: the tab bar shows once there are two.
const VIEWS = [{ id: 'answer', label: 'Answer' }];

/** No answer yet: what would produce one. */
const NotAnswered = ({ status }) => {
  let text = 'Not answered yet. Start the questionnaire to answer its questions, in order.';
  if (status === 'in_progress') text = 'Not answered yet: the run answers the questions in order.';
  else if (status === 'paused' || status === 'failed')
    text = 'Not answered yet. Resume the run to answer the remaining questions, in order.';
  return (
    <p className="rounded-lg border border-dashed border-border-hover p-4 text-sm text-content-secondary">
      {text}
    </p>
  );
};

/**
 * The selected question: its text, where it stands, and its answer with what
 * can be done with it (`review`: useAnswerReview), which also opens in a
 * window of its own. `sessionId`: the session of the page's address.
 * `runStatus`: the status of the questionnaire's run. `onBackToList`: on a
 * narrow screen, where the list sits above, goes back to it. `className`: the
 * panel's place in the layout.
 */
export const QuestionDetail = forwardRef(function QuestionDetail(
  { row, review, sessionId, runStatus, onBackToList, className = '' },
  ref
) {
  const [view, setView] = useState(VIEWS[0].id);
  const note = versionNote(row?.answer);

  return (
    <aside
      ref={ref}
      aria-label="The selected question"
      className={`scroll-mt-[calc(var(--navbar-height)_+_1rem)] rounded-xl border border-border bg-surface ${className}`}
    >
      {VIEWS.length > 1 && (
        <div
          role="tablist"
          aria-label="About this question"
          className="flex gap-1 border-b border-border p-2"
        >
          {VIEWS.map(item => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              onClick={() => setView(item.id)}
              className={`h-10 flex-1 rounded-lg px-3 text-sm font-semibold transition-colors ${FOCUS_RING} ${
                view === item.id
                  ? 'bg-surface-hover text-content'
                  : 'text-content-secondary hover:text-content'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}

      {row ? (
        <div className="space-y-5 p-5">
          <div>
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs text-content-muted">
                <span className="tabular-nums" title={row.code || undefined}>
                  {row.displayCode}
                </span>{' '}
                · {row.sectionTitle}
              </p>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={onBackToList}
                  className={`-my-2 inline-flex min-h-10 shrink-0 items-center gap-1 rounded text-xs text-link min-[1320px]:hidden ${FOCUS_RING}`}
                >
                  <ArrowUpIcon className="h-3.5 w-3.5" />
                  Back to the list
                </button>
                {/* Only an answered question has an answer to open. */}
                {row.answer && (
                  <OpenInWindow
                    href={`/session/${sessionId}/answer/${row.answer.id}`}
                    answerId={row.answer.id}
                  />
                )}
              </div>
            </div>
            {/* whitespace-pre-line: imported questions carry their instructions
                on their own lines (Level, Topic, Applies to...). */}
            <h2 className="mt-1 whitespace-pre-line text-base font-semibold leading-snug text-content">
              {row.text}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StateChip state={row.state} />
              {note && <span className="text-xs text-content-muted">{note}</span>}
            </div>
          </div>

          {view === 'answer' &&
            (row.answer ? (
              <AnswerPanel answer={row.answer} review={review} />
            ) : (
              <NotAnswered status={runStatus} />
            ))}
        </div>
      ) : (
        <EmptyState
          icon={CursorArrowRaysIcon}
          title="No question selected"
          text="Pick a question in the list to read its answer."
        />
      )}
    </aside>
  );
});
