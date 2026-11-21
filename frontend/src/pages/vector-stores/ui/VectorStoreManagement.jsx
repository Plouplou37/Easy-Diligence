import { useState } from 'react';
import { ArrowPathIcon, FolderOpenIcon, PlusIcon } from '@heroicons/react/24/outline';
import {
  CreateVectorStoreModal,
  useStoreSelection,
  useVectorStores,
} from '@/features/vector-store-manage';
import { Button, EmptyState, LoadingSpinner, PageHeader, pageLayout, panel } from '@/shared/ui';
import { VectorStoreDetails, VectorStoreList } from '@/widgets/vector-store-browser';

/** The document collections (OpenAI vector stores): the list, and the one selected. */
const VectorStoreManagement = () => {
  const stores = useVectorStores();
  const selection = useStoreSelection(stores.vectorStores);
  const [creating, setCreating] = useState(false);
  const { selected } = selection;

  // Every collection from OpenAI again, then the shown one's details.
  const refreshAll = async () => {
    await stores.loadVectorStores(true);
    if (selected) {
      const fresh = await stores.refreshSingleStore(selected.id);
      if (fresh) selection.setSelected(fresh);
    }
  };

  if (stores.loading && stores.vectorStores.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" text="Loading the documents…" />
      </div>
    );
  }

  const newCollection = (
    <Button onClick={() => setCreating(true)} variant="primary" icon={PlusIcon}>
      New collection
    </Button>
  );

  return (
    <div className={pageLayout.container}>
      <PageHeader
        title="Documents"
        subtitle={
          <span className="block max-w-3xl">
            The document collections the AI searches while it answers a due diligence. Each one is
            kept at OpenAI as a vector store, and deleted there after a set number of days without
            use (30 by default).
          </span>
        }
        actions={
          <>
            <Button
              onClick={refreshAll}
              loading={stores.loading}
              variant="secondary"
              icon={ArrowPathIcon}
              title="Ask OpenAI again, and remove the collections that have expired or disappeared there"
            >
              Refresh
            </Button>
            {newCollection}
          </>
        }
      />

      {stores.vectorStores.length === 0 ? (
        <div className={panel.base}>
          <EmptyState
            icon={FolderOpenIcon}
            title="No document collections yet"
            text="A collection holds the documents of a fund. Create one, add its files, then choose it when you start a due diligence."
            action={newCollection}
          />
        </div>
      ) : (
        <div className="flex flex-wrap items-start gap-6">
          <VectorStoreList
            stores={stores.vectorStores}
            selectedStore={selected}
            onSelectStore={selection.select}
          />
          <section
            aria-label="Selected collection"
            className={`${panel.base} min-w-0 flex-[999_1_520px] overflow-hidden`}
          >
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
              <p className="px-6 py-16 text-center text-sm text-content-muted">
                Select a collection to see its documents.
              </p>
            )}
          </section>
        </div>
      )}

      <CreateVectorStoreModal
        isOpen={creating}
        onClose={() => setCreating(false)}
        onCreate={stores.createStore}
      />
    </div>
  );
};

export default VectorStoreManagement;
