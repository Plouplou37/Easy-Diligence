import { useState, useEffect } from 'react';
import { vectorStoresAPI } from '../../../services/api';
import toast from 'react-hot-toast';

export const useVectorStores = () => {
  const [vectorStores, setVectorStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingStores, setDeletingStores] = useState(new Set());

  useEffect(() => {
    loadVectorStores();
  }, []);

  const loadVectorStores = async (clearCache = false) => {
    try {
      setLoading(true);

      // Clear cache if requested (manual refresh)
      if (clearCache) {
        try {
          await vectorStoresAPI.refresh();
        } catch (error) {
          console.warn('Cache refresh failed, continuing with data fetch:', error);
        }
      }

      const response = await vectorStoresAPI.list();
      setVectorStores(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      toast.error('Failed to load vector stores');
      setVectorStores([]);
    } finally {
      setLoading(false);
    }
  };

  const createStore = async (formData) => {
    try {
      await vectorStoresAPI.create(formData);
      toast.success('Vector store created successfully');
      await loadVectorStores();
      return true;
    } catch (error) {
      toast.error('Failed to create vector store');
      return false;
    }
  };

  const deleteStore = async (storeId) => {
    if (!confirm('Are you sure you want to delete this vector store? This action cannot be undone.')) {
      return false;
    }

    try {
      setDeletingStores(prev => new Set([...prev, storeId]));
      await vectorStoresAPI.delete(storeId);
      toast.success('Vector store deleted successfully');
      await loadVectorStores();
      return true;
    } catch (error) {
      toast.error(error.message || 'Failed to delete vector store');
      return false;
    } finally {
      setDeletingStores(prev => {
        const newSet = new Set(prev);
        newSet.delete(storeId);
        return newSet;
      });
    }
  };

  const refreshSingleStore = async (storeId) => {
    if (!storeId) return null;

    try {
      // Clear cache for this specific store
      await vectorStoresAPI.refreshStore(storeId);

      // Fetch detailed store info from OpenAI (includes file_count, total_bytes, status)
      const detailedResponse = await vectorStoresAPI.get(storeId);
      const detailedStore = detailedResponse.data;

      // Update the vectorStores list with the detailed store data
      setVectorStores(prev =>
        prev.map(store => store.id === storeId ? detailedStore : store)
      );

      // Return the detailed store object
      return detailedStore;
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
    refreshSingleStore
  };
};
