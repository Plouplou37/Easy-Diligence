import { useId, useState } from 'react';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  TrashIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { formatBytes } from '@/shared/lib/format';
import { Button } from '@/shared/ui';

const STATUS_ICONS = {
  uploading: <ArrowPathIcon className="h-4 w-4 text-accent-blue animate-spin" />,
  success: <CheckCircleIcon className="h-4 w-4 text-theme-success" />,
  error: <XCircleIcon className="h-4 w-4 text-theme-error" title="Upload failed" />,
};

/** Choose or drop files, see them listed, send them. `upload`: useFileUpload. */
const FileUploader = ({ upload }) => {
  const inputId = useId();
  const [dragging, setDragging] = useState(false);
  const { stagedFiles, uploadLoading } = upload;
  const pending = stagedFiles.filter(file => file.status === 'pending').length;

  const drop = event => {
    event.preventDefault();
    setDragging(false);
    upload.addFiles(event.dataTransfer.files);
  };

  return (
    <div
      onDragOver={event => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={drop}
      className={`border-2 border-dashed transition-colors rounded-lg p-6 ${
        dragging ? 'border-accent-blue bg-accent-blue/5' : 'border-border hover:border-accent-blue'
      }`}
    >
      <input
        type="file"
        multiple
        onChange={event => {
          upload.addFiles(event.target.files);
          event.target.value = ''; // the same file can be chosen again
        }}
        className="hidden"
        id={inputId}
      />
      <label htmlFor={inputId} className="cursor-pointer flex flex-col items-center justify-center">
        <CloudArrowUpIcon className="h-12 w-12 text-content-muted mb-2" />
        <span className="text-sm text-content-secondary">
          Click to select files, or drop them here
        </span>
        <span className="text-xs text-content-muted mt-1">
          PDF, Word, PowerPoint, Excel, CSV, text, Markdown, HTML or JSON. The server checks type
          and size.
        </span>
      </label>

      {stagedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-content-secondary">
              Files ({stagedFiles.length})
            </h4>
            <Button
              onClick={upload.confirmUpload}
              disabled={pending === 0}
              loading={uploadLoading}
              variant="success"
              size="sm"
            >
              Upload {pending > 0 ? `(${pending})` : ''}
            </Button>
          </div>

          {stagedFiles.map(file => (
            <div key={file.id} className="flex items-center justify-between p-2 form-surface">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-content truncate">{file.name}</div>
                <div className="text-xs text-content-muted">{formatBytes(file.size)}</div>
              </div>
              <div className="flex items-center space-x-2 ml-2">
                {file.status === 'pending' || file.status === 'error' ? (
                  <>
                    {STATUS_ICONS[file.status]}
                    <Button
                      variant="danger"
                      size="sm"
                      icon={TrashIcon}
                      onClick={() => upload.removeStagedFile(file.id)}
                      aria-label={`Remove ${file.name}`}
                    />
                  </>
                ) : (
                  STATUS_ICONS[file.status]
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileUploader;
