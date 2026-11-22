import { PlusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { getSourceContent } from '@/entities/answer';
import { Button, Input } from '@/shared/ui';
import SourceContent from './SourceContent';

const TYPE_LABELS = { file_search: 'Document', web: 'Web page', web_search: 'Web search' };

/**
 * The sources of an answer being edited: the user may add or remove their own.
 * `title` (null for none) and `className` fit it in a panel that has its own.
 */
const SourcesManager = ({
  editingSources,
  newSource,
  setNewSource,
  onAddSource,
  onRemoveSource,
  title = 'Sources',
  className = 'border-t border-border pt-3',
}) => (
  <div className={className}>
    {title && <h4 className="text-sm font-medium text-content mb-2">{title}</h4>}

    <div className="space-y-2 mb-3">
      {editingSources.map((source, index) =>
        getSourceContent(source) === null ? null : (
          <div key={index} className="flex items-center justify-between gap-2 form-surface p-2">
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium text-content-secondary">
                {TYPE_LABELS[source.type] || 'File'}
                {source.user_added && <span className="ml-1 text-accent-blue">(added by you)</span>}
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
                className="h-10 w-10 shrink-0"
                aria-label="Remove source"
              />
            )}
          </div>
        )
      )}
    </div>

    <div className="border-t border-border pt-3">
      <h5 className="text-xs font-medium text-content-secondary mb-2">Add a source</h5>
      <div className="flex flex-wrap gap-2">
        <select
          value={newSource.type}
          onChange={event => setNewSource({ ...newSource, type: event.target.value })}
          className="form-input h-10 py-0 text-sm"
          aria-label="Source type"
        >
          <option value="web">Web page</option>
          <option value="file">File</option>
        </select>
        <Input
          value={newSource.content}
          onChange={event => setNewSource({ ...newSource, content: event.target.value })}
          placeholder={newSource.type === 'web' ? 'https://example.com' : 'File name'}
          aria-label="Source"
          className="min-w-40 flex-1"
        />
        <Button variant="secondary" icon={PlusIcon} onClick={onAddSource}>
          Add
        </Button>
      </div>
    </div>
  </div>
);

export default SourcesManager;
