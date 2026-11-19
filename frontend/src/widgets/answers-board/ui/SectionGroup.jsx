import { ChevronDownIcon, ChevronUpIcon, FolderIcon } from '@heroicons/react/24/outline';
import { panel } from '@/shared/ui';

/** A questionnaire section, folded or not, and its answers (`renderAnswer`). */
const SectionGroup = ({ sectionName, answers, isExpanded, onToggle, renderAnswer }) => (
  <div className={`${panel.base} overflow-hidden`}>
    <button
      type="button"
      className="w-full text-left px-6 py-4 border-b border-border hover:bg-surface-hover transition-colors"
      onClick={onToggle}
      aria-expanded={Boolean(isExpanded)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <FolderIcon className="h-5 w-5 text-content-muted" />
          <h2 className="text-lg font-medium text-content">{sectionName}</h2>
          <span className="text-sm text-content-muted">
            ({answers.length} {answers.length === 1 ? 'question' : 'questions'})
          </span>
        </div>
        {isExpanded ? (
          <ChevronUpIcon className="h-5 w-5 text-content-muted" />
        ) : (
          <ChevronDownIcon className="h-5 w-5 text-content-muted" />
        )}
      </div>
    </button>

    <div
      className={`divide-y divide-border overflow-hidden transition-all duration-300 ease-in-out ${
        isExpanded ? 'max-h-[10000px] opacity-100' : 'max-h-0 opacity-0'
      }`}
    >
      <div
        className={`transition-transform duration-300 ${isExpanded ? 'translate-y-0' : '-translate-y-2'}`}
      >
        {answers.map(renderAnswer)}
      </div>
    </div>
  </div>
);

export default SectionGroup;
