import { forwardRef } from 'react';
import { FolderIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { Button, EmptyState, Input, LoadingSpinner } from '@/shared/ui';
import { STATES, STATE_ORDER } from '../lib/questionnaire';
import { FOCUS_RING, FOCUS_RING_INSET } from '../lib/focus';
import { StateChip } from './Chips';

const placeholderOf = row => {
  if (row.state === 'failed') return 'The AI could not answer this question';
  return row.state === 'none' ? 'Not answered yet' : '';
};

const QuestionRow = ({ row, selected, onSelect }) => (
  <li className="border-b border-border last:border-b-0">
    <button
      type="button"
      data-row-key={row.key}
      onClick={() => onSelect(row.key, { reveal: true })}
      aria-pressed={selected}
      className={`flex min-h-11 w-full items-start gap-3 border-l-[3px] px-4 py-3 text-left transition-colors ${FOCUS_RING_INSET} ${
        selected
          ? 'border-l-primary bg-primary-dark'
          : 'border-l-transparent hover:bg-surface-hover'
      }`}
    >
      {/* The full code stays reachable on hover: it is the unique id. */}
      <span
        className="w-12 shrink-0 pt-px text-xs font-semibold text-content-secondary tabular-nums"
        title={row.code || undefined}
      >
        {row.displayCode}
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="line-clamp-2 text-sm font-medium text-content">{row.text}</span>
        <span className="truncate text-[0.8125rem] text-content-secondary">
          {row.snippet || placeholderOf(row)}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1.5">
        <StateChip state={row.state} />
        {row.sources > 0 && (
          <span className="text-[0.6875rem] text-content-muted tabular-nums">
            {row.sources} source{row.sources === 1 ? '' : 's'}
          </span>
        )}
      </span>
    </button>
  </li>
);

/** Rows, under their section's name when the list holds several sections. */
const groupRows = rows => {
  const groups = [];
  rows.forEach(row => {
    const last = groups[groups.length - 1];
    if (last && last.key === row.sectionKey) last.rows.push(row);
    else groups.push({ key: row.sectionKey, title: row.sectionTitle, rows: [row] });
  });
  return groups;
};

const FilterChip = ({ label, count, pressed, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    aria-pressed={pressed}
    className={`inline-flex h-10 items-center gap-1.5 rounded-full border px-3.5 text-xs font-medium transition-colors ${FOCUS_RING} ${
      pressed
        ? 'border-primary bg-primary-dark text-content'
        : 'border-border text-content-secondary hover:bg-surface-hover hover:text-content'
    }`}
  >
    {label}
    <span className="tabular-nums text-content-muted">{count}</span>
  </button>
);

/**
 * The questions of the selected questionnaire: the section's title, a search,
 * a status filter, and one row per question (`review`: useQuestionnaireReview,
 * `filters`: useQuestionFilters). Up and down arrows move the selection.
 */
export const QuestionList = forwardRef(function QuestionList(
  { review, filters, sectionLabel, selectedKey, onSelect },
  ref
) {
  const rows = filters.filtered;
  const groups = groupRows(rows);
  const severalSections = groups.length > 1 || !filters.section;

  const moveSelection = event => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    const buttons = [...event.currentTarget.querySelectorAll('[data-row-key]')];
    const index = buttons.indexOf(document.activeElement);
    if (index === -1) return;
    event.preventDefault();
    const next = buttons[index + (event.key === 'ArrowDown' ? 1 : -1)];
    if (next) {
      next.focus();
      onSelect(next.dataset.rowKey);
    }
  };

  let body;
  if (review.loading) {
    body = <LoadingSpinner text="Loading the questions…" className="py-12" />;
  } else if (review.failed) {
    body = (
      <EmptyState
        icon={FolderIcon}
        title="The answers could not be loaded"
        action={
          <Button variant="secondary" onClick={() => review.reload()}>
            Try again
          </Button>
        }
      />
    );
  } else if (review.total === 0) {
    body = (
      <EmptyState
        icon={FolderIcon}
        title="No question yet"
        text="This questionnaire has no question, or none could be listed."
      />
    );
  } else if (rows.length === 0) {
    body = (
      <EmptyState
        icon={MagnifyingGlassIcon}
        title="No question matches"
        text="Try another search, section or status."
      />
    );
  } else {
    body = (
      <div onKeyDown={moveSelection}>
        {groups.map(group => (
          <div key={group.key}>
            {severalSections && (
              <h3 className="border-b border-border bg-surface-bg px-4 py-2 text-xs font-semibold text-content-secondary">
                {group.title}
              </h3>
            )}
            <ul>
              {group.rows.map(row => (
                <QuestionRow
                  key={row.key}
                  row={row}
                  selected={row.key === selectedKey}
                  onSelect={onSelect}
                />
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }

  const countLine = filters.active
    ? `${rows.length} of ${review.total} questions`
    : `${review.total} questions · ${review.done} answered`;

  return (
    <section
      ref={ref}
      aria-labelledby="question-list-title"
      className="min-w-0 scroll-mt-[calc(var(--navbar-height)_+_1rem)] overflow-hidden rounded-xl border border-border bg-surface"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <h2 id="question-list-title" className="text-base font-semibold text-content">
            {sectionLabel}
          </h2>
          {!review.loading && review.total > 0 && (
            <p className="text-xs text-content-muted tabular-nums">{countLine}</p>
          )}
        </div>
        <Input
          type="search"
          value={filters.searchTerm}
          onChange={event => filters.setSearchTerm(event.target.value)}
          placeholder="Search questions and answers"
          aria-label="Search the questions and answers"
          leftIcon={MagnifyingGlassIcon}
          className="w-full sm:w-72"
        />
      </div>

      {!review.loading && review.total > 0 && (
        <div
          role="group"
          aria-label="Filter by status"
          className="flex flex-wrap gap-1.5 border-b border-border px-4 py-2.5"
        >
          <FilterChip
            label="All"
            count={filters.counts.all}
            pressed={!filters.state}
            onClick={() => filters.setState('')}
          />
          {STATE_ORDER.filter(state => filters.counts[state] > 0 || filters.state === state).map(
            state => (
              <FilterChip
                key={state}
                label={STATES[state].label}
                count={filters.counts[state]}
                pressed={filters.state === state}
                onClick={() => filters.setState(filters.state === state ? '' : state)}
              />
            )
          )}
        </div>
      )}

      {review.structureMissing && !review.loading && (
        <p className="alert alert-warning m-4">
          The questions of this questionnaire could not be loaded: only the answered ones are
          listed.
        </p>
      )}

      {body}
    </section>
  );
});
