import { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { field, panel, sectionHeader } from '@/shared/ui';

/** Search and section filter, folded by default. `filters`: useAnswerFilters. */
const AnswerFilters = ({ filters }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className={`${panel.base} mb-6`}>
      <div className="px-5 py-4">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between gap-3 w-full text-left"
          aria-expanded={open}
        >
          <h3 className={sectionHeader.title}>Filters & Search</h3>
          <span className={sectionHeader.hairline} />
          {open ? (
            <ChevronUpIcon className="w-5 h-5 text-content-muted" />
          ) : (
            <ChevronDownIcon className="w-5 h-5 text-content-muted" />
          )}
        </button>

        {open && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label htmlFor="answer-search" className={field.label}>
                Search
              </label>
              <div className="relative">
                <MagnifyingGlassIcon className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-content-muted pointer-events-none" />
                <input
                  id="answer-search"
                  type="text"
                  value={filters.searchTerm}
                  onChange={(event) => filters.setSearchTerm(event.target.value)}
                  placeholder="Search questions or answers..."
                  className="block w-full rounded-md input-gradient-border pl-10 pr-3 py-2 text-sm text-content"
                />
              </div>
            </div>

            <div>
              <label htmlFor="answer-section" className={field.label}>
                Section
              </label>
              <select
                id="answer-section"
                value={filters.section}
                onChange={(event) => filters.setSection(event.target.value)}
                className="form-input w-full px-3 py-2 text-sm"
              >
                <option value="">All Sections</option>
                {filters.sections.map((section) => (
                  <option key={section} value={section}>
                    {section}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnswerFilters;
