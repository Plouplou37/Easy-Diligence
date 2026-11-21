import { ArrowPathIcon, DocumentIcon } from '@heroicons/react/24/outline';
import { isUnknown, storeProblem } from '@/entities/vector-store';
import { plural } from '@/features/session-create';
import { formatBytes } from '@/shared/lib/format';
import { AiBadge, Badge, Button, LoadingSpinner } from '@/shared/ui';
import { UploadZone } from './UploadZone';

// The indexing state of a file at OpenAI.
const FILE_STATES = {
  completed: { tone: 'success', label: 'Ready' },
  in_progress: { tone: 'warning', label: 'Indexing…' },
  failed: { tone: 'error', label: 'Failed' },
  cancelled: { tone: 'error', label: 'Cancelled' },
};

/** How long the collection lasts. `fallbackDays`: the days chosen at its creation. */
const expiryNote = (store, fallbackDays) => {
  const kept = 'Kept at OpenAI, in a vector store.';
  if (isUnknown(store)) return `${kept} Its expiry is unknown for now.`;
  const days = store.expires_after_days ?? fallbackDays;
  const date = store.expires_at ? new Date(store.expires_at).toLocaleDateString() : null;
  if (!days && !date) return kept;
  const after = days ? ` after ${plural(days, 'day')} without use` : '';
  const on = date ? ` (on ${date}, unless a run uses it first)` : '';
  return `${kept} It expires${after}${on}; the Documents page flags it a week before.`;
};

const FileRows = ({ files }) => {
  if (files.filesLoading) return <LoadingSpinner size="sm" />;
  if (files.filesError) {
    return <p className="alert alert-warning m-4">{files.filesError}</p>;
  }
  if (files.files.length === 0) {
    return (
      <p className="px-4 py-3 text-sm text-content-muted">
        No file yet: add the fund&apos;s documents below.
      </p>
    );
  }
  return (
    <ul className="max-h-72 overflow-y-auto">
      {files.files.map(file => {
        const state = FILE_STATES[file.status];
        return (
          <li
            key={file.id}
            className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-border px-4 py-2.5 last:border-b-0"
          >
            <DocumentIcon aria-hidden="true" className="h-4 w-4 shrink-0 text-content-muted" />
            <span
              className={`min-w-0 flex-[1_1_12rem] text-sm break-all ${
                file.details_missing ? 'italic text-content-muted' : 'text-content'
              }`}
            >
              {file.filename}
            </span>
            {Number.isFinite(file.size_bytes) && (
              <span className="text-xs text-content-muted tabular-nums">
                {formatBytes(file.size_bytes)}
              </span>
            )}
            {state && (
              <Badge variant={state.tone} size="sm">
                {state.label}
              </Badge>
            )}
          </li>
        );
      })}
    </ul>
  );
};

/**
 * The chosen collection: its files, the upload of more, and its expiry.
 * `documents`: useDocumentsChoice.
 */
export const CollectionPanel = ({ documents, errors }) => {
  const { chosen: store, files, upload, created, form } = documents;
  const problem = storeProblem(store);
  const fallbackDays = created?.id === store.id ? Number(form.days) : null;

  return (
    <div className="overflow-hidden rounded-xl border border-border">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-surface-bg px-4 py-2">
        <span className="min-w-0 py-1.5 font-semibold text-content break-words">{store.name}</span>
        <div className="flex items-center gap-2">
          <AiBadge>Searched by the AI</AiBadge>
          <Button
            type="button"
            variant="ghost"
            size="lg"
            icon={ArrowPathIcon}
            onClick={documents.refresh}
            loading={documents.refreshing}
            aria-label="Refresh the files of this collection"
            title="Ask OpenAI again: a file being indexed shows as ready once it is"
          />
        </div>
      </div>

      {problem && <p className="alert alert-warning m-4">{problem}</p>}
      <FileRows files={files} />

      <div className="border-t border-border p-4">
        <UploadZone upload={upload} errors={errors} />
      </div>

      <p className="border-t border-border px-4 py-2.5 text-xs text-content-muted">
        {expiryNote(store, fallbackDays)}
      </p>
    </div>
  );
};
