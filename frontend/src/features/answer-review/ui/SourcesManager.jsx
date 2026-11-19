import { PlusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { getSourceContent } from '@/entities/answer';
import { Button } from '@/shared/ui';
import SourceContent from './SourceContent';

const TYPE_LABELS = { file_search: 'Vector Store', web: 'Web URL', web_search: 'Web Search' };

/** The sources of an answer being edited: the user may add or remove their own. */
const SourcesManager = ({
  editingSources,
  newSource,
  setNewSource,
  onAddSource,
  onRemoveSource,
}) => (
  <div className="border-t border-border pt-3">
    <h5 className="text-sm font-medium text-content mb-2">Sources</h5>

    <div className="space-y-2 mb-3">
      {editingSources.map((source, index) =>
        getSourceContent(source) === null ? null : (
          <div key={index} className="flex items-center justify-between form-surface p-2">
            <div className="flex-1">
              <div className="text-xs font-medium text-content-secondary">
                {TYPE_LABELS[source.type] || 'File'}
                {source.user_added && <span className="ml-1 text-accent-blue">(User Added)</span>}
              </div>
              <div className="text-xs text-content-secondary break-all">
                <SourceContent source={source} />
              </div>
            </div>
            {source.user_added && (
              <Button
                variant="danger"
                icon={XMarkIcon}
                onClick={() => onRemoveSource(index)}
                className="ml-2 flex-shrink-0"
                aria-label="Remove source"
              />
            )}
          </div>
        )
      )}
    </div>

    <div className="border-t border-border pt-3">
      <h6 className="text-xs font-medium text-content-secondary mb-2">Add New Source</h6>
      <div className="flex gap-2">
        <select
          value={newSource.type}
          onChange={event => setNewSource({ ...newSource, type: event.target.value })}
          className="form-input px-2 py-1 text-xs"
          aria-label="Source type"
        >
          <option value="web">Web URL</option>
          <option value="file">File</option>
        </select>
        <input
          type="text"
          value={newSource.content}
          onChange={event => setNewSource({ ...newSource, content: event.target.value })}
          placeholder={newSource.type === 'web' ? 'https://example.com' : 'Filename or path'}
          className="form-input flex-1 px-2 py-1 text-xs"
          aria-label="Source"
        />
        <Button size="sm" icon={PlusIcon} onClick={onAddSource}>
          Add
        </Button>
      </div>
    </div>
  </div>
);

export default SourcesManager;
