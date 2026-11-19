import { useState } from 'react';
import { ArrowPathIcon, FolderOpenIcon, PlusIcon } from '@heroicons/react/24/outline';
import { CreateVectorStoreModal, useStoreSelection, useVectorStores } from '@/features/vector-store-manage';
import { Button, EmptyState, LoadingSpinner, PageHeader, pageLayout, panel } from '@/shared/ui';
import { VectorStoreDetails, VectorStoreList } from '@/widgets/vector-store-browser';

const VectorStoreManagement = () => {
  const stores = useVectorStores();
  const selection = useStoreSelection(stores.vectorStores);
  const [creating, setCreating] = useState(false);
  const { selected } = selection;

  // Every store from OpenAI again, then the shown one's details.
  const refreshAll = async () => {
    await stores.loadVectorStores(true);
    if (selected) {
      const fresh = await stores.refreshSingleStore(selected.id);
      if (fresh) selection.setSelected(fresh);
    }
  };

  if (stores.loading && stores.vectorStores.length === 0) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" text="Loading vector stores..." />
      </div>
    );
  }

  return (
    <div className={`${pageLayout.container} h-full flex flex-col`}>
      <div className="flex-shrink-0">
        <PageHeader
          breadcrumb={[{ label: 'Vector Stores' }]}
          title="Vector Store Management"
          subtitle="Manage the document collections the engine searches during a due diligence"
          actions={
            <>
              <Button onClick={refreshAll} loading={stores.loading} variant="secondary" icon={ArrowPathIcon}>
                Refresh
              </Button>
              <Button onClick={() => setCreating(true)} variant="primary" icon={PlusIcon}>
                Create New Vector Store
              </Button>
            </>
          }
        />
      </div>

      <div className="flex-1 min-h-0 overflow-hidden">
        {stores.vectorStores.length === 0 ? (
          <EmptyState
            className="h-full flex flex-col justify-center"
            icon={FolderOpenIcon}
            title="No vector stores"
            text="Get started by creating a new vector store."
            action={
              <Button onClick={() => setCreating(true)} variant="primary" icon={PlusIcon}>
                Create Vector Store
              </Button>
            }
          />
        ) : (
          <div className="flex gap-6 h-full overflow-hidden">
            <VectorStoreList stores={stores.vectorStores} selectedStore={selected} onSelectStore={selection.select} />
            <div className={`${panel.base} flex-1 flex flex-col overflow-hidden`}>
              {selected ? (
                <VectorStoreDetails
                  key={selected.id}
                  store={selected}
                  refreshStore={stores.refreshSingleStore}
                  onRefreshed={selection.setSelected}
                  deleting={stores.deletingStores.has(selected.id)}
                  onDelete={stores.deleteStore}
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-sm text-content-muted">
                  Select a vector store to view details
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <CreateVectorStoreModal isOpen={creating} onClose={() => setCreating(false)} onCreate={stores.createStore} />
    </div>
  );
};

export default VectorStoreManagement;
