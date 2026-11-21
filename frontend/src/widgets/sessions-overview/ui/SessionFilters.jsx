import { useState } from 'react';
import { AdjustmentsHorizontalIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { SESSION_STATUS_OPTIONS } from '@/shared/lib/status';
import { Button, SearchInput } from '@/shared/ui';

const PERIODS = [
  ['all', 'Any time'],
  ['today', 'Today'],
  ['week', 'Last 7 days'],
  ['month', 'Last 30 days'],
];

const SORTS = [
  ['activity', 'Latest activity'],
  ['review', 'Most to review'],
  ['recent', 'Newest first'],
  ['oldest', 'Oldest first'],
  ['name', 'Name (A to Z)'],
  ['progress', 'Most progress'],
];

// On a phone, each control takes the whole width, its label aligned on the others.
const Select = ({ id, label, value, onChange, children }) => (
  <div className="flex w-full items-center gap-2 sm:w-auto">
    <label htmlFor={id} className="w-16 shrink-0 text-xs font-medium text-content-muted sm:w-auto">
      {label}
    </label>
    <select
      id={id}
      className="form-input h-10 min-w-0 flex-1 cursor-pointer text-sm sm:flex-none"
      value={value}
      onChange={e => onChange(e.target.value)}
    >
      {children}
    </select>
  </div>
);

/**
 * The toolbar above the list: search, status, creation date, sort, and "with
 * answers to review". On a phone the filters fold behind a button.
 * `filters`: useSessionFilters.
 */
export const SessionFilters = ({ filters }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3 sm:px-5">
      <SearchInput
        className="min-w-0 grow basis-48 sm:basis-80 [&_input]:h-10"
        value={filters.search}
        onChange={filters.setSearch}
        placeholder="Search"
        aria-label="Search the due diligences"
        title="Searches the name, the fund, the management company and the questionnaires"
      />
      <Button
        variant="secondary"
        icon={AdjustmentsHorizontalIcon}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="dashboard-filters"
        className="sm:hidden"
      >
        Filters{filters.filterCount > 0 && ` (${filters.filterCount})`}
      </Button>

      {/* From the small screens up, the filters sit in the toolbar itself. */}
      <div
        id="dashboard-filters"
        className={`${open ? 'flex' : 'hidden'} w-full flex-col gap-3 sm:contents`}
      >
        <Select
          id="status-filter"
          label="Status"
          value={filters.status}
          onChange={filters.setStatus}
        >
          <option value="all">All statuses</option>
          {SESSION_STATUS_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
        <Select
          id="date-filter"
          label="Created"
          value={filters.period}
          onChange={filters.setPeriod}
        >
          {PERIODS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select id="sort-by" label="Sort" value={filters.sortBy} onChange={filters.setSortBy}>
          {SORTS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <label
          className={`inline-flex h-10 w-full cursor-pointer items-center gap-2 whitespace-nowrap rounded-lg border px-3 text-sm transition-colors sm:w-auto ${
            filters.reviewOnly
              ? 'border-primary bg-primary-dark text-content'
              : 'border-border-hover text-content-secondary hover:bg-surface-hover hover:text-content'
          }`}
        >
          <input
            type="checkbox"
            className="h-4 w-4 rounded-sm"
            checked={filters.reviewOnly}
            onChange={event => filters.setReviewOnly(event.target.checked)}
          />
          With answers to review
        </label>
        {filters.active && (
          <Button variant="ghost" icon={XMarkIcon} onClick={filters.reset}>
            Clear
          </Button>
        )}
      </div>
    </div>
  );
};
