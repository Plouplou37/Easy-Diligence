import { useState } from 'react';
import { ChevronDownIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { SESSION_STATUS_OPTIONS } from '@/shared/lib/status';
import { Button, SearchInput, field, panel } from '@/shared/ui';

const PERIODS = [
  ['all', 'All Time'],
  ['today', 'Today'],
  ['week', 'Last 7 Days'],
  ['month', 'Last 30 Days'],
];

const SORTS = [
  ['activity', 'Latest Activity'],
  ['review', 'Most to Review'],
  ['recent', 'Newest First'],
  ['oldest', 'Oldest First'],
  ['name', 'Name (A-Z)'],
  ['progress', 'Progress (%)'],
];

const Select = ({ id, label, value, onChange, children }) => (
  <div>
    <label htmlFor={id} className={field.label}>
      {label}
    </label>
    <select
      id={id}
      className={`${field.input} py-2 text-sm`}
      value={value}
      onChange={e => onChange(e.target.value)}
    >
      {children}
    </select>
  </div>
);

/** The search, and the filters folded behind a button. `filters`: useSessionFilters. */
export const SessionFilters = ({ filters }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className={`${panel.base} p-5`}>
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput
          className="flex-1"
          value={filters.search}
          onChange={filters.setSearch}
          placeholder="Search sessions by name, fund, management company or DD type..."
        />
        <Button
          variant="secondary"
          onClick={() => setOpen(!open)}
          icon={FunnelIcon}
          aria-expanded={open}
        >
          Filters
          <ChevronDownIcon
            className={`w-4 h-4 transform transition-transform ${open ? 'rotate-180' : ''}`}
          />
        </Button>
      </div>

      {open && (
        <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 gap-4 sm:grid-cols-4">
          <Select
            id="status-filter"
            label="Status"
            value={filters.status}
            onChange={filters.setStatus}
          >
            <option value="all">All Statuses</option>
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
          <Select id="sort-by" label="Sort By" value={filters.sortBy} onChange={filters.setSortBy}>
            {SORTS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <label className="flex items-end gap-2 pb-2 text-sm text-content cursor-pointer">
            <input
              type="checkbox"
              className="w-4 h-4 rounded-sm"
              checked={filters.reviewOnly}
              onChange={event => filters.setReviewOnly(event.target.checked)}
            />
            With answers to review
          </label>
        </div>
      )}
    </div>
  );
};
