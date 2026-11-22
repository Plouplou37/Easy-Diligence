import { useDeferredValue, useId } from 'react';
import {
  ArrowUturnLeftIcon,
  CheckBadgeIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { AnswerMarkdown } from '@/features/answer-review';
import { Button, Input, tabs } from '@/shared/ui';

// On a narrow card, one of the two at a time.
const VIEWS = [
  { id: 'edit', label: 'Edit' },
  { id: 'preview', label: 'Preview' },
];

// The two panes share a height: tall, and still with room for the bar below.
const PANE_HEIGHT = 'h-[62vh] min-h-80';

/** What the bar says about the draft, and in which tone. */
const statusOf = ({ regenerating, changed, approved }) => {
  if (regenerating)
    return {
      text: 'Regenerating… Saving and approving wait for the new answer.',
      tone: 'text-theme-ai',
    };
  if (changed)
    return {
      text: 'Unsaved changes. Save them before approving: a saved edit is a new version, to review.',
      tone: 'text-theme-warning',
    };
  if (approved)
    return { text: 'Approved. An edit sends it back to review.', tone: 'text-content-muted' };
  return { text: 'No unsaved changes.', tone: 'text-content-muted' };
};

/**
 * The answer's text, as markdown, with its preview beside it on a wide card
 * (Edit and Preview tabs on a narrow one), the reason for the change, and
 * the actions, kept in view at the bottom of the window while the card is.
 * `work`: useAnswerWork. `view` and `onViewChange`: the tab shown when narrow.
 */
export const AnswerEditorCard = ({ work, view, onViewChange }) => {
  const id = useId();
  const { answer, draft, regenerating } = work;
  // Typing stays fluid on a long answer: the preview follows a moment later.
  const preview = useDeferredValue(draft.text);
  const approved = answer.status === 'approved';
  const canSave = draft.changed && !regenerating && !draft.saving;
  const status = statusOf({ regenerating, changed: draft.changed, approved });

  // Ctrl+S (⌘S) saves, from the text or the reason.
  const onKeyDown = event => {
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 's') return;
    event.preventDefault();
    if (canSave) work.save();
  };

  return (
    <section
      aria-labelledby={`${id}-title`}
      onKeyDown={onKeyDown}
      className="@container rounded-xl border border-border bg-surface"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3">
        <h2 id={`${id}-title`} className="text-base font-semibold text-content">
          Answer
        </h2>
        <div role="group" aria-label="Shown" className={`${tabs.group} @3xl:hidden`}>
          {VIEWS.map(item => (
            <button
              key={item.id}
              type="button"
              aria-pressed={view === item.id}
              onClick={() => onViewChange(item.id)}
              className={`${tabs.tab} min-h-10 ${view === item.id ? tabs.active : tabs.inactive}`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="hidden text-xs text-content-muted @3xl:block">
          Markdown on the left, as it reads on the right.
        </p>
      </div>

      <div className="grid gap-5 p-5 @3xl:grid-cols-2">
        <div className={view === 'edit' ? '' : 'hidden @3xl:block'}>
          <label htmlFor={`${id}-text`} className="eyebrow mb-1.5 block">
            Markdown
          </label>
          {/* Monospace: this is markdown source, and pipe tables are
              unreadable in a proportional font. */}
          <textarea
            id={`${id}-text`}
            value={draft.text}
            onChange={event => draft.setText(event.target.value)}
            readOnly={draft.saving}
            placeholder="Write the answer, in markdown…"
            className={`form-input block w-full resize-y px-3 py-2 font-mono text-sm leading-relaxed ${PANE_HEIGHT}`}
          />
        </div>
        <div className={view === 'preview' ? '' : 'hidden @3xl:block'}>
          <p id={`${id}-preview`} className="eyebrow mb-1.5">
            Preview
          </p>
          <div
            role="region"
            aria-labelledby={`${id}-preview`}
            className={`form-surface overflow-y-auto px-4 py-3 ${PANE_HEIGHT}`}
          >
            {preview.trim() ? (
              <AnswerMarkdown>{preview}</AnswerMarkdown>
            ) : (
              <p className="text-sm text-content-muted">Nothing to preview: the answer is empty.</p>
            )}
          </div>
        </div>
      </div>

      <div className="sticky bottom-0 z-10 rounded-b-xl border-t border-border bg-surface px-5 py-4">
        <div className="flex flex-wrap items-end gap-3">
          <Input
            id={`${id}-reason`}
            label="Reason for the change (optional)"
            value={draft.reason}
            onChange={event => draft.setReason(event.target.value)}
            placeholder="E.g. figures checked against the annual report"
            className="min-w-0 flex-[1_1_280px]"
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              icon={CheckIcon}
              onClick={work.save}
              loading={draft.saving}
              disabled={!canSave}
              title="Save (Ctrl+S)"
            >
              Save
            </Button>
            <Button
              variant={approved ? 'secondary' : 'success'}
              icon={approved ? ArrowUturnLeftIcon : CheckBadgeIcon}
              onClick={work.toggleStatus}
              loading={work.statusPending}
              disabled={regenerating || (!approved && draft.changed)}
            >
              {approved ? 'Back to review' : 'Approve'}
            </Button>
            {draft.changed && (
              <Button
                variant="ghost"
                icon={XMarkIcon}
                onClick={work.discard}
                disabled={draft.saving}
              >
                Discard changes
              </Button>
            )}
          </div>
        </div>
        <p aria-live="polite" className={`mt-2 text-xs ${status.tone}`}>
          {status.text}
        </p>
      </div>
    </section>
  );
};
