import React from 'react';
import { MagnifyingGlassIcon, ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/24/outline';
import { field, panel, sectionHeader } from '../../../components/ui';

const AnswerFilters = ({
  showFilters,
  setShowFilters,
  searchTerm,
  setSearchTerm,
  selectedSection,
  setSelectedSection,
  uniqueSections
}) => {
  return (
    <div className={`${panel.base} mb-6`}>
      <div className="px-5 py-4">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center justify-between gap-3 w-full text-left"
        >
          <h3 className={sectionHeader.title}>
            Filters & Search
          </h3>
          <span className={sectionHeader.hairline} />
          {showFilters ? (
            <ChevronUpIcon className="w-5 h-5 text-content-muted" />
          ) : (
            <ChevronDownIcon className="w-5 h-5 text-content-muted" />
          )}
        </button>

        {showFilters && (
          <div className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className={field.label}>
                  Search
                </label>
                <div className="relative">
                  <MagnifyingGlassIcon className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-content-muted pointer-events-none" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search questions or answers..."
                    className="block w-full rounded-md input-gradient-border pl-10 pr-3 py-2 text-sm text-content"
                  />
                </div>
              </div>

              <div>
                <label className={field.label}>
                  Section
                </label>
                <select
                  value={selectedSection}
                  onChange={(e) => setSelectedSection(e.target.value)}
                  className="form-input w-full px-3 py-2 text-sm"
                >
                  <option value="">All Sections</option>
                  {uniqueSections.map(section => (
                    <option key={section} value={section}>{section}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnswerFilters;
