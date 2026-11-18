import React from 'react';
import { XMarkIcon, PlusIcon, LinkIcon } from '@heroicons/react/24/outline';
import { Button } from '../../../components/ui';

const SourcesManager = ({
  editingSources,
  newSource,
  setNewSource,
  onAddSource,
  onRemoveSource,
  renderSourceContent
}) => {
  return (
    <div className="border-t border-border pt-3">
      <h5 className="text-sm font-medium text-content mb-2">Sources</h5>

      <div className="space-y-2 mb-3">
        {editingSources.map((source, index) => {
          const content = renderSourceContent(source);
          if (!content) return null;

          return (
            <div key={index} className="flex items-center justify-between form-surface p-2">
              <div className="flex-1">
                <div className="text-xs font-medium text-content-secondary">
                  {source.type === 'file_search' ? 'Vector Store' :
                   source.type === 'web' ? 'Web URL' :
                   source.type === 'web_search' ? 'Web Search' : 'File'}
                  {source.user_added && <span className="ml-1 text-accent-blue">(User Added)</span>}
                </div>
                <div className="text-xs text-content-secondary break-all">
                  {content}
                </div>
              </div>
              {source.user_added && (
                <Button
                  variant="danger"
                  icon={XMarkIcon}
                  onClick={() => onRemoveSource(index)}
                  className="ml-2 flex-shrink-0"
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="border-t border-border pt-3">
        <h6 className="text-xs font-medium text-content-secondary mb-2">Add New Source</h6>
        <div className="flex gap-2">
          <select
            value={newSource.type}
            onChange={(e) => setNewSource({ ...newSource, type: e.target.value })}
            className="form-input px-2 py-1 text-xs"
          >
            <option value="web">Web URL</option>
            <option value="file">File</option>
          </select>
          <input
            type="text"
            value={newSource.content}
            onChange={(e) => setNewSource({ ...newSource, content: e.target.value })}
            placeholder={newSource.type === 'web' ? 'https://example.com' : 'Filename or path'}
            className="form-input flex-1 px-2 py-1 text-xs"
          />
          <Button
            size="sm"
            onClick={onAddSource}
          >
            <PlusIcon className="w-3 h-3" />
            Add
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SourcesManager;
