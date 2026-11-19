import React, { useState, useEffect } from 'react';
import {
  PlusIcon,
  TrashIcon,
  ArrowPathIcon,
  FolderOpenIcon,
  DocumentIcon,
  TagIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import { Modal } from '@/shared/ui';
import { Button, EmptyState, LoadingSpinner, PageHeader, field, pageLayout, panel, sectionHeader } from '@/shared/ui';
import { VectorStoreList } from '@/widgets/vector-store-browser';
import { FileList } from '@/widgets/vector-store-browser';
import { FileUploadModal } from '@/features/vector-store-manage';
import { useVectorStores } from '@/features/vector-store-manage';
import { useFileUpload } from '@/features/vector-store-manage';
import { useFileManagement } from '@/features/vector-store-manage';
import { formatBytes } from '@/shared/lib/format';
import { vectorStoresAPI } from '@/entities/vector-store';

const VectorStoreManagement = () => {
  const [selectedStore, setSelectedStore] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    expires_after_days: 30
  });

  const { vectorStores, loading, deletingStores, loadVectorStores, createStore, deleteStore, refreshSingleStore } = useVectorStores();

  const fileManagement = useFileManagement(selectedStore, () => refreshSingleStore(selectedStore?.id));
  const fileUpload = useFileUpload(selectedStore, async () => {
    const refreshedStore = await refreshSingleStore(selectedStore?.id);
    if (refreshedStore) {
      setSelectedStore(refreshedStore);
      await fileManagement.loadFiles();
    }
    setShowUploadModal(false);
  });

  useEffect(() => {
    if (vectorStores.length > 0 && !selectedStore) {
      handleSelectStore(vectorStores[0]);
    }
  }, [vectorStores, selectedStore]);

  const handleSelectStore = async (store) => {
    if (selectedStore?.id !== store?.id) {
      // Set basic store info immediately for responsive UI
      setSelectedStore(store);

      // Fetch detailed info from OpenAI in background
      try {
        const response = await vectorStoresAPI.get(store.id);
        if (response.data) {
          setSelectedStore(response.data);
        }
      } catch (error) {
        console.error('Failed to fetch store details:', error);
      }
    }
  };

  const handleCreateStore = async (e) => {
    e.preventDefault();
    const success = await createStore(createForm);
    if (success) {
      setShowCreateModal(false);
      setCreateForm({ name: '', description: '', expires_after_days: 30 });
    }
  };

  const handleRefreshStore = async () => {
    if (!selectedStore) return;
    setRefreshing(true);
    try {
      const refreshedStore = await refreshSingleStore(selectedStore.id);
      if (refreshedStore) {
        setSelectedStore(refreshedStore);
        await fileManagement.loadFiles();
      }
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <>
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner size="lg" text="Loading vector stores..." />
        </div>
      </>
    );
  }

  return (
    <>
      <div className={`${pageLayout.container} h-full flex flex-col`}>
        <div className="flex-shrink-0">
          <PageHeader
            breadcrumb={[{ label: 'Vector Stores' }]}
            title="Vector Store Management"
            subtitle="Manage the document collections the engine searches during a due diligence"
            actions={(
              <>
                <Button
                  onClick={async () => {
                    await loadVectorStores(true);
                    // Re-fetch details for currently selected store after global refresh
                    if (selectedStore) {
                      const refreshedStore = await refreshSingleStore(selectedStore.id);
                      if (refreshedStore) {
                        setSelectedStore(refreshedStore);
                      }
                    }
                  }}
                  disabled={loading}
                  loading={loading}
                  variant="secondary"
                  icon={ArrowPathIcon}
                >
                  Refresh
                </Button>
                <Button
                  onClick={() => setShowCreateModal(true)}
                  variant="primary"
                  icon={PlusIcon}
                >
                  Create New Vector Store
                </Button>
              </>
            )}
          />
        </div>

        <div className="flex-1 min-h-0 overflow-hidden">
          {vectorStores.length === 0 ? (
            <EmptyState
              className="h-full flex flex-col justify-center"
              icon={FolderOpenIcon}
              title="No vector stores"
              text="Get started by creating a new vector store."
              action={(
                <Button onClick={() => setShowCreateModal(true)} variant="primary" icon={PlusIcon}>
                  Create Vector Store
                </Button>
              )}
            />
          ) : (
            <div className="flex gap-6 h-full overflow-hidden">
              <VectorStoreList
                stores={vectorStores}
                selectedStore={selectedStore}
                onSelectStore={handleSelectStore}
              />

              <div className={`${panel.base} flex-1 flex flex-col overflow-hidden`}>
                {selectedStore ? (
                  <>
                    <div className="p-5 border-b border-border flex-shrink-0">
                      <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                          {/* The OpenAI id is internal: kept in the tooltip. */}
                          <h2 className="text-fluid-lg font-medium text-content" title={`ID: ${selectedStore.id}`}>
                            {selectedStore.name}
                          </h2>
                          {selectedStore.description && (
                            <p className="text-sm text-content-secondary mt-1 line-clamp-2" title={selectedStore.description}>
                              {selectedStore.description}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            onClick={handleRefreshStore}
                            disabled={refreshing}
                            loading={refreshing}
                            variant="ghost"
                            icon={ArrowPathIcon}
                          />
                          <Button
                            onClick={() => deleteStore(selectedStore.id)}
                            disabled={deletingStores.has(selectedStore.id)}
                            loading={deletingStores.has(selectedStore.id)}
                            variant="danger"
                            icon={TrashIcon}
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div className="bg-surface-bg rounded-md p-3">
                          <div className="eyebrow">Files</div>
                          <div className="mt-1 text-lg font-medium text-content">
                            {selectedStore.file_count}
                          </div>
                        </div>
                        <div className="bg-surface-bg rounded-md p-3">
                          <div className="eyebrow">Size</div>
                          <div className="mt-1 text-lg font-medium text-content">
                            {formatBytes(selectedStore.total_bytes)}
                          </div>
                        </div>
                        <div className="bg-surface-bg rounded-md p-3">
                          <div className="eyebrow">Expires</div>
                          <div
                            className="mt-1 text-lg font-medium text-content"
                            title={selectedStore.expires_at ? new Date(selectedStore.expires_at).toLocaleString() : undefined}
                          >
                            {selectedStore.expires_at
                              ? new Date(selectedStore.expires_at).toLocaleDateString()
                              : 'Never'}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex-1 min-h-0 flex flex-col p-5">
                      <div className="flex items-center justify-between gap-4 mb-4 flex-shrink-0">
                        <div className={`${sectionHeader.wrapper} flex-1`}>
                          <h3 className={sectionHeader.title}>
                            {/* No count while loading: "Files (0)" read as an empty store. */}
                            {fileManagement.filesLoading ? 'Files' : `Files (${fileManagement.files.length})`}
                          </h3>
                          <div className={sectionHeader.hairline} />
                        </div>
                        <Button
                          onClick={() => setShowUploadModal(true)}
                          variant="primary"
                          icon={PlusIcon}
                        >
                          Upload Files
                        </Button>
                      </div>
                      <div className="flex-1 min-h-0">
                        <FileList
                          key={selectedStore?.id}
                          files={fileManagement.files}
                          loading={fileManagement.filesLoading}
                          onRemoveFile={fileManagement.removeFile}
                        />
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-sm text-content-muted">
                    Select a vector store to view details
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create New Vector Store">
          <form onSubmit={handleCreateStore} className="space-y-4">
            <div>
              <label className={field.label}>
                Name
              </label>
              <input
                type="text"
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                className="form-input w-full"
                required
              />
            </div>
            <div>
              <label className={field.label}>
                Description
              </label>
              <textarea
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                className="form-input w-full"
                rows={3}
              />
            </div>
            <div>
              <label className={field.label}>
                Expires After (days)
              </label>
              <input
                type="number"
                value={createForm.expires_after_days}
                onChange={(e) => setCreateForm({ ...createForm, expires_after_days: parseInt(e.target.value) })}
                className="form-input w-full"
                min="1"
                max="365"
              />
            </div>
            <div className="flex justify-end space-x-2 pt-4">
              <Button
                type="button"
                onClick={() => setShowCreateModal(false)}
                variant="secondary"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
              >
                Create
              </Button>
            </div>
          </form>
        </Modal>

        <FileUploadModal
          show={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          stagedFiles={fileUpload.stagedFiles}
          onFileSelect={fileUpload.handleFileSelection}
          onRemoveFile={fileUpload.removeStagedFile}
          onConfirmUpload={fileUpload.confirmUpload}
          uploading={fileUpload.uploadLoading}
        />
      </div>
    </>
  );
};

export default VectorStoreManagement;
