import { useRef, useState } from 'react';
import { ArrowUpTrayIcon, DocumentIcon, TrashIcon } from '@heroicons/react/24/outline';
import { FieldError, plural } from '@/features/session-create';
import { formatBytes } from '@/shared/lib/format';
import { Badge, Button, LoadingSpinner } from '@/shared/ui';

const StagedState = ({ status }) => {
  if (status === 'uploading') {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-content-muted">
        <LoadingSpinner size="sm" inline />
        Uploading…
      </span>
    );
  }
  if (status === 'error')
    return (
      <Badge variant="error" size="sm">
        Failed
      </Badge>
    );
  return <span className="text-xs text-content-muted">To upload</span>;
};

/**
 * Drop or choose the fund's documents, then send them to the chosen
 * collection. `upload`: useFileUpload (features/vector-store-manage).
 * `errors`: keyed by the id of the control to use ('docs-choose', 'docs-upload').
 */
export const UploadZone = ({ upload, errors }) => {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const { stagedFiles, uploadLoading } = upload;
  const pending = stagedFiles.filter(file => file.status === 'pending').length;
  const error = errors['docs-choose'] || errors['docs-upload'];

  return (
    <div className="flex flex-col gap-3">
      <div
        onDragOver={event => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={event => {
          event.preventDefault();
          setDragging(false);
          upload.addFiles(event.dataTransfer.files);
        }}
        className={`flex flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
          dragging ? 'border-primary bg-primary-dark' : 'border-border-hover'
        }`}
      >
        <ArrowUpTrayIcon aria-hidden="true" className="h-7 w-7 text-content-secondary" />
        <p className="font-semibold text-content">Drop the fund&apos;s documents here</p>
        <p className="max-w-prose text-[0.8125rem] text-content-secondary">
          Prospectus, factsheets, annual reports, presentations, DDQ. PDF, Word, PowerPoint, Excel,
          CSV, text, Markdown, HTML or JSON; the server checks the type and the size.
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          tabIndex={-1}
          aria-hidden="true"
          className="hidden"
          onChange={event => {
            upload.addFiles(event.target.files);
            event.target.value = ''; // the same file can be chosen again
          }}
        />
        <Button
          type="button"
          id="docs-choose"
          variant="secondary"
          className="mt-2"
          onClick={() => inputRef.current?.click()}
          aria-describedby={errors['docs-choose'] ? 'docs-upload-error' : undefined}
        >
          Choose files
        </Button>
      </div>

      {stagedFiles.length > 0 && (
        <div className="flex flex-col gap-2">
          <ul className="overflow-hidden rounded-xl border border-border">
            {stagedFiles.map(file => (
              <li
                key={file.id}
                className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-border px-4 py-2 last:border-b-0"
              >
                <DocumentIcon aria-hidden="true" className="h-4 w-4 shrink-0 text-content-muted" />
                <span className="min-w-0 flex-[1_1_12rem] text-sm text-content break-all">
                  {file.name}
                </span>
                <span className="text-xs text-content-muted tabular-nums">
                  {formatBytes(file.size)}
                </span>
                <StagedState status={file.status} />
                {(file.status === 'pending' || file.status === 'error') && (
                  <Button
                    type="button"
                    variant="danger"
                    size="lg"
                    icon={TrashIcon}
                    onClick={() => upload.removeStagedFile(file.id)}
                    aria-label={`Remove ${file.name}`}
                    title="Remove"
                  />
                )}
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <Button
              type="button"
              id="docs-upload"
              variant="secondary"
              icon={ArrowUpTrayIcon}
              onClick={upload.confirmUpload}
              loading={uploadLoading}
              disabled={pending === 0}
              aria-describedby={errors['docs-upload'] ? 'docs-upload-error' : undefined}
            >
              {pending > 0 ? `Upload ${plural(pending, 'file')}` : 'Upload'}
            </Button>
          </div>
        </div>
      )}

      <FieldError id="docs-upload-error">{error}</FieldError>
    </div>
  );
};
