import { useRef, useState } from 'react';
import {
  ArrowPathIcon,
  ArrowUpTrayIcon,
  DocumentIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { formatBytes } from '@/shared/lib/format';
import { Badge, Button, modalStyles } from '@/shared/ui';

// Where each chosen file stands (useFileUpload).
const STATES = {
  pending: { label: 'To upload', variant: 'neutral' },
  uploading: { label: 'Uploading…', variant: 'info' },
  success: { label: 'Uploaded', variant: 'success' },
  error: { label: 'Failed', variant: 'error' },
};

/**
 * Choose or drop files, see them listed, send them; the window's buttons
 * below. `upload`: useFileUpload. `onClose` closes the window.
 */
const FileUploader = ({ upload, onClose }) => {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const { stagedFiles, uploadLoading } = upload;
  const pending = stagedFiles.filter(file => file.status === 'pending').length;
  const failed = stagedFiles.filter(file => file.status === 'error').length;

  const drop = event => {
    event.preventDefault();
    setDragging(false);
    // A file dropped during a send would be dropped from the list at its end.
    if (!uploadLoading) upload.addFiles(event.dataTransfer.files);
  };

  return (
    <>
      <div className="space-y-5">
        <div
          onDragOver={event => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={drop}
          className={`rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
            dragging ? 'border-accent-blue bg-primary-dark' : 'border-border-hover'
          }`}
        >
          <ArrowUpTrayIcon className="mx-auto h-7 w-7 text-content-secondary" aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold text-content">Drop the fund’s documents here</p>
          <p className="mt-1 text-sm text-content-secondary">
            Prospectus, factsheets, annual reports, presentations, DDQ.
          </p>
          <p className="mt-1 text-xs text-content-muted">
            PDF, Word, PowerPoint, Excel, CSV, text, Markdown, HTML or JSON. The server checks the
            type and size of each file.
          </p>
          <input
            ref={inputRef}
            type="file"
            multiple
            onChange={event => {
              upload.addFiles(event.target.files);
              event.target.value = ''; // the same file can be chosen again
            }}
            className="hidden"
            tabIndex={-1}
            aria-hidden="true"
          />
          <Button
            type="button"
            variant="secondary"
            className="mt-4"
            onClick={() => inputRef.current?.click()}
            disabled={uploadLoading}
          >
            Choose files
          </Button>
        </div>

        {stagedFiles.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-content">
              Files
              <span className="ml-2 font-normal tabular-nums text-content-muted">
                {stagedFiles.length}
              </span>
            </h3>
            <ul className="mt-2 divide-y divide-border overflow-hidden rounded-lg border border-border">
              {stagedFiles.map(file => {
                const state = STATES[file.status] || STATES.pending;
                const removable = file.status === 'pending' || file.status === 'error';
                return (
                  <li key={file.id} className="flex items-center gap-3 py-1.5 pl-3 pr-1.5">
                    <DocumentIcon
                      className="h-4 w-4 shrink-0 text-content-muted"
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-content" title={file.name}>
                        {file.name}
                      </p>
                      <p className="text-xs tabular-nums text-content-muted">
                        {formatBytes(file.size)}
                      </p>
                    </div>
                    <Badge variant={state.variant} size="sm">
                      {file.status === 'uploading' && (
                        <ArrowPathIcon className="h-3 w-3 animate-spin" aria-hidden="true" />
                      )}
                      {state.label}
                    </Badge>
                    {removable ? (
                      <Button
                        variant="ghost"
                        size="lg"
                        icon={XMarkIcon}
                        onClick={() => upload.removeStagedFile(file.id)}
                        title="Remove from the list"
                        aria-label={`Remove ${file.name} from the list`}
                      />
                    ) : (
                      <span className="w-10 shrink-0" aria-hidden="true" />
                    )}
                  </li>
                );
              })}
            </ul>
            {failed > 0 && !uploadLoading && (
              <p className="mt-2 text-xs text-theme-error">
                The failed files stay listed so you can see which: remove them, then add them again
                to retry.
              </p>
            )}
          </div>
        )}
      </div>

      <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
        <Button type="button" variant="secondary" onClick={onClose} disabled={uploadLoading}>
          {pending > 0 ? 'Cancel' : 'Close'}
        </Button>
        <Button
          type="button"
          variant="primary"
          icon={ArrowUpTrayIcon}
          onClick={upload.confirmUpload}
          disabled={pending === 0}
          loading={uploadLoading}
        >
          {pending > 1 ? `Upload ${pending} files` : 'Upload'}
        </Button>
      </div>
    </>
  );
};

export default FileUploader;
