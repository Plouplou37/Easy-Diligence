import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { vectorStoresAPI } from '@/entities/vector-store';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';

/** The user's vector stores: list, creation, deletion, refresh of one. */
export const useVectorStores = () => {
  const confirm = useConfirm();
  const [vectorStores, setVectorStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingStores, setDeletingStores] = useState(new Set());

  // clearCache: the manual refresh, which asks OpenAI again.
  const loadVectorStores = useCallback(async (clearCache = false) => {
    setLoading(true);
    try {
      if (clearCache) {
        try {
          await vectorStoresAPI.refresh();
        } catch (error) {
          console.warn('Cache refresh failed, continuing with data fetch:', error);
        }
      }
      const response = await vectorStoresAPI.list();
      setVectorStores(Array.isArray(response.data) ? response.data : []);
    } catch {
      toast.error('Failed to load vector stores');
      setVectorStores([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVectorStores();
  }, [loadVectorStores]);

  const createStore = async formData => {
    try {
      await vectorStoresAPI.create(formData);
      toast.success('Vector store created successfully');
      await loadVectorStores();
      return true;
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to create vector store'));
      return false;
    }
  };

  const deleteStore = async storeId => {
    const store = vectorStores.find(item => item.id === storeId);
    const confirmed = await confirm({
      title: 'Delete vector store',
      message:
        `Delete ${store?.name ? `"${store.name}"` : 'this vector store'} and its files? ` +
        'The sessions it is assigned to lose these documents. This cannot be undone.',
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return false;

    setDeletingStores(previous => new Set([...previous, storeId]));
    try {
      await vectorStoresAPI.delete(storeId);
      toast.success('Vector store deleted successfully');
      await loadVectorStores();
      return true;
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to delete vector store'));
      return false;
    } finally {
      setDeletingStores(previous => {
        const next = new Set(previous);
        next.delete(storeId);
        return next;
      });
    }
  };

  // The store's details (file count, size, status), fresh from OpenAI.
  const refreshSingleStore = async storeId => {
    if (!storeId) return null;
    try {
      await vectorStoresAPI.refreshStore(storeId);
      const response = await vectorStoresAPI.get(storeId);
      setVectorStores(previous =>
        previous.map(store => (store.id === storeId ? response.data : store))
      );
      return response.data;
    } catch (error) {
      console.warn('Failed to refresh store:', error);
      return null;
    }
  };

  return {
    vectorStores,
    loading,
    deletingStores,
    loadVectorStores,
    createStore,
    deleteStore,
    refreshSingleStore,
  };
};
