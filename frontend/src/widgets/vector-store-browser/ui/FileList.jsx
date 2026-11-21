import { DocumentIcon, ExclamationTriangleIcon, TrashIcon } from '@heroicons/react/24/outline';
import { formatBytes } from '@/shared/lib/format';
import { Badge, Button, EmptyState, LoadingSpinner } from '@/shared/ui';

// OpenAI listed the file but did not give its details: the backend sends
// `details_missing`, and does not cache that answer.
const MISSING_DETAILS = "OpenAI did not return this file's details. Refresh to ask again.";

// The state of a document at OpenAI: the AI can search it once it is ready.
const FILE_STATES = {
  completed: { label: 'Ready', variant: 'success' },
  in_progress: {
    label: 'Indexing…',
    variant: 'info',
    title: 'OpenAI is still reading this document: it can be searched once ready.',
  },
  failed: { label: 'Failed', variant: 'error', title: 'OpenAI could not index this document.' },
  cancelled: { label: 'Cancelled', variant: 'neutral' },
};

/** The day the file was added (OpenAI gives seconds), or null. */
const addedOn = file =>
  Number.isFinite(file.created_at) ? new Date(file.created_at * 1000).toLocaleDateString() : null;

const FileState = ({ file }) => {
  const state = FILE_STATES[file.status];
  if (!state) return null;
  const title = file.status === 'failed' && file.last_error?.message;
  return (
    <span title={title || state.title}>
      <Badge variant={state.variant} size="sm">
        {state.label}
      </Badge>
    </span>
  );
};

const FileList = ({ files, loading, error, onRemoveFile }) => {
  if (loading) {
    return <LoadingSpinner size="md" text="Loading the documents…" className="py-10" />;
  }

  // The listing failed: the collection may well hold files, so never "No documents".
  if (error) {
    return (
      <div className="alert alert-error flex items-start gap-2" role="alert">
        <ExclamationTriangleIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-semibold">The documents could not be listed</p>
          <p className="mt-0.5">{error}</p>
        </div>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border-hover">
        <EmptyState
          icon={DocumentIcon}
          title="No documents in this collection yet"
          text="Add the fund's documents: prospectus, factsheets, reports, presentations."
        />
      </div>
    );
  }

  return (
    <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
      {files.map(file => {
        const added = addedOn(file);
        return (
          <li
            key={file.id}
            className="flex flex-wrap items-center gap-x-4 gap-y-1 py-1.5 pl-4 pr-1.5 transition-colors hover:bg-surface-hover"
          >
            <DocumentIcon className="h-4 w-4 shrink-0 text-content-muted" aria-hidden="true" />
            <span
              className={`min-w-0 flex-[1_1_12rem] truncate text-sm ${
                file.details_missing ? 'italic text-content-muted' : 'font-medium text-content'
              }`}
              title={
                file.details_missing
                  ? `${MISSING_DETAILS} ID: ${file.id}`
                  : `${file.filename} · ID: ${file.id}`
              }
            >
              {file.filename}
            </span>
            <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
              {Number.isFinite(file.size_bytes) && (
                <span className="text-xs tabular-nums text-content-muted">
                  {formatBytes(file.size_bytes)}
                </span>
              )}
              {added && (
                <span className="text-xs tabular-nums text-content-muted">Added {added}</span>
              )}
              <FileState file={file} />
            </span>
            <Button
              onClick={() => onRemoveFile(file.id)}
              variant="danger"
              size="lg"
              icon={TrashIcon}
              className="ml-auto"
              title="Remove this document"
              aria-label={`Remove ${file.filename}`}
            />
          </li>
        );
      })}
    </ul>
  );
};

export default FileList;
