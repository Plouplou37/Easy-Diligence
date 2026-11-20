import { useState } from 'react';
import { CheckCircleIcon, ExclamationTriangleIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { getDdTypeIcon } from '@/entities/dd-type';
import { Button, EmptyState, SearchInput } from '@/shared/ui';
import { categoriesOf, ddTypeCategory } from '../lib/ddTypeCategory';

// Below this many types, the search and the categories only get in the way.
const FILTER_FROM = 7;

const DdTypeTile = ({ ddType, selected, onToggle }) => {
  const Icon = getDdTypeIcon(ddType);
  return (
    <label
      className={`relative flex flex-col h-36 p-4 rounded-lg cursor-pointer ${
        selected ? 'border border-accent-blue bg-accent-blue/5' : 'gradient-grey-border-hover'
      }`}
    >
      <input type="checkbox" checked={selected} onChange={onToggle} className="sr-only" />
      <span
        aria-hidden="true"
        className={`absolute top-3 right-3 w-5 h-5 rounded-full border-2 transition-all duration-200 ${
          selected ? 'bg-accent-blue border-accent-blue' : 'border-border'
        }`}
      >
        {selected && <CheckCircleIcon className="w-5 h-5 text-content-inverse" />}
      </span>
      <span className="mb-3 p-2 rounded-lg inline-flex items-center justify-center bg-surface-bg self-start">
        <Icon className={`w-6 h-6 ${selected ? 'text-accent-blue' : 'text-content-secondary'}`} />
      </span>
      <span className="flex-1">
        <span className="block text-sm font-semibold mb-1 leading-tight text-content">
          {ddType.name}
        </span>
        {ddType.description && (
          <span
            className="block text-xs leading-relaxed line-clamp-2 overflow-hidden text-content-secondary"
            title={ddType.description}
          >
            {ddType.description}
          </span>
        )}
      </span>
    </label>
  );
};

/** Pick the DD types of a session: `selected` is a list of codes. */
export const DdTypePicker = ({ ddTypes, selected, onChange }) => {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const categories = categoriesOf(ddTypes);
  const term = search.toLowerCase();

  const shown = ddTypes.filter(
    ddType =>
      (!term ||
        ddType.name.toLowerCase().includes(term) ||
        ddType.description?.toLowerCase().includes(term)) &&
      (category === 'all' || ddTypeCategory(ddType.name) === category)
  );
  const filtering = Boolean(term) || category !== 'all';

  const toggle = code =>
    onChange(
      selected.includes(code) ? selected.filter(item => item !== code) : [...selected, code]
    );

  return (
    <>
      {ddTypes.length >= FILTER_FROM && (
        <div className="mb-6 space-y-4">
          <SearchInput
            placeholder="Search due diligence types..."
            value={search}
            onChange={setSearch}
          />
          {categories.length > 1 && (
            <div className="flex flex-wrap items-center gap-2">
              <FunnelIcon className="h-4 w-4 text-content-muted" />
              <span className="eyebrow mr-2">Filter by category:</span>
              {[{ key: 'all', label: 'All', count: ddTypes.length }, ...categories].map(item => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setCategory(item.key)}
                  data-active={category === item.key}
                  aria-pressed={category === item.key}
                  className="pill-action"
                >
                  {item.label} ({item.count})
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mb-4 flex items-center justify-between">
        <div className="text-sm text-content-secondary">
          {selected.length > 0
            ? `${selected.length} of ${ddTypes.length} types selected`
            : 'No types selected'}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() =>
              onChange([...new Set([...selected, ...shown.map(ddType => ddType.code)])])
            }
            className="text-xs text-link"
          >
            Select All {filtering ? 'Filtered' : ''}
          </button>
          <span className="text-border">|</span>
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-xs text-content-secondary hover:text-content"
          >
            Clear All
          </button>
        </div>
      </div>

      {shown.length === 0 ? (
        <EmptyState
          icon={FunnelIcon}
          title="No due diligence types found matching your criteria."
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearch('');
                setCategory('all');
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {shown.map(ddType => (
            <DdTypeTile
              key={ddType.code}
              ddType={ddType}
              selected={selected.includes(ddType.code)}
              onToggle={() => toggle(ddType.code)}
            />
          ))}
        </div>
      )}

      {selected.length === 0 && (
        <p className="alert alert-error mt-4 flex items-center gap-2">
          <ExclamationTriangleIcon className="w-4 h-4 shrink-0" />
          Please select at least one due diligence type to continue.
        </p>
      )}
    </>
  );
};
