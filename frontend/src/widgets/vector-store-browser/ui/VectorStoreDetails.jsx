import { useState } from 'react';
import {
  ArrowPathIcon,
  ArrowUpTrayIcon,
  ExclamationTriangleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { expiryLevel, isStale, isUnknown, storeProblem, storeState } from '@/entities/vector-store';
import { FileUploadModal, useFileManagement, useFileUpload } from '@/features/vector-store-manage';
import { formatBytes } from '@/shared/lib/format';
import { AiBadge, Button } from '@/shared/ui';
import FileList from './FileList';

// The colour of the expiry date once it is near (entities/vector-store, expiryLevel).
const EXPIRY_TONES = { imminent: 'text-theme-error', soon: 'text-theme-warning' };

const Figure = ({ label, value, hint, title, tone = 'text-content' }) => (
  <div className="form-surface min-w-0 flex-[1_1_9rem] px-4 py-3">
    <dt className="text-xs text-content-muted">{label}</dt>
    <dd
      className={`mt-0.5 truncate text-xl font-semibold tracking-tight tabular-nums ${tone}`}
      title={title}
    >
      {value}
    </dd>
    {hint && <dd className="mt-0.5 text-xs text-content-muted">{hint}</dd>}
  </div>
);

/**
 * One document collection (an OpenAI vector store): its figures, its
 * documents, the upload and the deletion. `refreshStore(id)` fetches it again
 * and resolves to the fresh store, which `onRefreshed` receives.
 */
const VectorStoreDetails = ({ store, refreshStore, onRefreshed, deleting, onDelete }) => {
  const [refreshing, setRefreshing] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  const refresh = async () => {
    const fresh = await refreshStore(store.id);
    if (fresh) onRefreshed(fresh);
    return fresh;
  };

  // A collection gone at OpenAI has no files to list: asking would only fail.
  const stale = isStale(store);
  const known = !stale && !isUnknown(store);
  const problem = storeProblem(store);
  const files = useFileManagement(stale ? null : store, refresh);
  const upload = useFileUpload(store, async ({ failed }) => {
    await refresh();
    await files.loadFiles();
    if (failed === 0) setUploadOpen(false);
  });

  const refreshAll = async () => {
    setRefreshing(true);
    try {
      await refresh();
      await files.loadFiles();
    } finally {
      setRefreshing(false);
    }
  };

  const expires = store.expires_at ? new Date(store.expires_at) : null;
  let expiry = expires ? expires.toLocaleDateString() : 'Never';
  if (!known) expiry = storeState(store)?.label || '—';
  const days = store.expires_after_days;
  const expiryHint =
    known && days ? `After ${days} day${days === 1 ? '' : 's'} without use` : undefined;
  const expiryTone = EXPIRY_TONES[known ? expiryLevel(store) : null];

  // No count while loading or after a failure: "0" would read as an empty collection.
  const countKnown = !files.filesLoading && !stale && !files.filesError;

  return (
    <>
      <div className="space-y-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-[1_1_16rem]">
            <p className="eyebrow">Document collection</p>
            {/* The OpenAI id is internal: kept in the tooltip. */}
            <h2
              className="mt-1 break-words text-xl font-semibold tracking-tight text-content"
              title={`OpenAI vector store ID: ${store.id}`}
            >
              {store.name}
            </h2>
            {store.description && (
              <p className="mt-1 whitespace-pre-line text-sm text-content-secondary">
                {store.description}
              </p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              onClick={refreshAll}
              loading={refreshing}
              variant="secondary"
              icon={ArrowPathIcon}
              title="Ask OpenAI again for this collection's figures and documents"
            >
              Refresh
            </Button>
            <Button
              onClick={() => onDelete(store.id)}
              loading={deleting}
              variant="danger"
              size="lg"
              icon={TrashIcon}
              title="Delete this collection"
              aria-label="Delete this collection"
            />
          </div>
        </div>

        <dl className="flex flex-wrap gap-3">
          <Figure label="Files" value={known ? store.file_count : '—'} />
          <Figure label="Size" value={known ? formatBytes(store.total_bytes) : '—'} />
          <Figure
            label="Expires"
            value={expiry}
            hint={expiryHint}
            tone={expiryTone}
            title={known && expires ? expires.toLocaleString() : undefined}
          />
        </dl>

        {problem && (
          <div
            className={`alert ${stale ? 'alert-error' : 'alert-warning'} flex items-start gap-2`}
          >
            <ExclamationTriangleIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
            <p>
              {problem}
              {stale &&
                ' Delete it here, or use Refresh at the top of the page to remove every collection in this state.'}
            </p>
          </div>
        )}
      </div>

      <div className="border-t border-border p-5 sm:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h3 className="text-base font-semibold text-content">
              Documents
              {countKnown && (
                <span className="ml-2 text-sm font-normal tabular-nums text-content-muted">
                  {files.files.length}
                </span>
              )}
            </h3>
            {!stale && <AiBadge>Searched by the AI</AiBadge>}
          </div>
          {!stale && (
            <Button onClick={() => setUploadOpen(true)} variant="secondary" icon={ArrowUpTrayIcon}>
              Add files
            </Button>
          )}
        </div>

        {stale ? (
          <p className="text-sm text-content-muted">
            No documents: they went with the collection at OpenAI.
          </p>
        ) : (
          <>
            <FileList
              files={files.files}
              loading={files.filesLoading}
              error={files.filesError}
              onRemoveFile={files.removeFile}
            />
            <p className="mt-3 text-xs text-content-muted">
              The AI does not read them whole: for each question, it searches them and reads the
              passages it finds.
            </p>
          </>
        )}
      </div>

      <FileUploadModal isOpen={uploadOpen} onClose={() => setUploadOpen(false)} upload={upload} />
    </>
  );
};

export default VectorStoreDetails;
