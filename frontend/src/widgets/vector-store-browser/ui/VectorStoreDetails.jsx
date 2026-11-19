import { useState } from 'react';
import { ArrowPathIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import { FileUploadModal, useFileManagement, useFileUpload } from '@/features/vector-store-manage';
import { formatBytes } from '@/shared/lib/format';
import { Button, sectionHeader } from '@/shared/ui';
import FileList from './FileList';

const Figure = ({ label, value, title }) => (
  <div className="bg-surface-bg rounded-md p-3">
    <div className="eyebrow">{label}</div>
    <div className="mt-1 text-lg font-medium text-content" title={title}>
      {value}
    </div>
  </div>
);

/**
 * One vector store: its figures, its files, the upload and the deletion.
 * `refreshStore(id)` fetches it again and resolves to the fresh store, which
 * `onRefreshed` receives.
 */
const VectorStoreDetails = ({ store, refreshStore, onRefreshed, deleting, onDelete }) => {
  const [refreshing, setRefreshing] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  const refresh = async () => {
    const fresh = await refreshStore(store.id);
    if (fresh) onRefreshed(fresh);
    return fresh;
  };

  const files = useFileManagement(store, refresh);
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

  return (
    <>
      <div className="p-5 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            {/* The OpenAI id is internal: kept in the tooltip. */}
            <h2 className="text-fluid-lg font-medium text-content" title={`ID: ${store.id}`}>
              {store.name}
            </h2>
            {store.description && (
              <p
                className="text-sm text-content-secondary mt-1 line-clamp-2"
                title={store.description}
              >
                {store.description}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={refreshAll}
              loading={refreshing}
              variant="ghost"
              icon={ArrowPathIcon}
              title="Refresh this vector store"
              aria-label="Refresh this vector store"
            />
            <Button
              onClick={() => onDelete(store.id)}
              loading={deleting}
              variant="danger"
              icon={TrashIcon}
              title="Delete this vector store"
              aria-label="Delete this vector store"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <Figure label="Files" value={store.file_count} />
          <Figure label="Size" value={formatBytes(store.total_bytes)} />
          <Figure
            label="Expires"
            value={expires ? expires.toLocaleDateString() : 'Never'}
            title={expires ? expires.toLocaleString() : undefined}
          />
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col p-5">
        <div className="flex items-center justify-between gap-4 mb-4 flex-shrink-0">
          <div className={`${sectionHeader.wrapper} flex-1`}>
            <h3 className={sectionHeader.title}>
              {/* No count while loading: "Files (0)" read as an empty store. */}
              {files.filesLoading ? 'Files' : `Files (${files.files.length})`}
            </h3>
            <div className={sectionHeader.hairline} />
          </div>
          <Button onClick={() => setUploadOpen(true)} variant="primary" icon={PlusIcon}>
            Upload Files
          </Button>
        </div>
        <div className="flex-1 min-h-0">
          <FileList
            files={files.files}
            loading={files.filesLoading}
            onRemoveFile={files.removeFile}
          />
        </div>
      </div>

      <FileUploadModal isOpen={uploadOpen} onClose={() => setUploadOpen(false)} upload={upload} />
    </>
  );
};

export default VectorStoreDetails;
