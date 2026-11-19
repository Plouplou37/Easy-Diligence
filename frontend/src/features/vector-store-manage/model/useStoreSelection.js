import { useCallback, useEffect, useState } from 'react';
import { vectorStoresAPI } from '@/entities/vector-store';

/**
 * The vector store shown in detail: the first one by default, its list entry
 * at once, then its details from OpenAI (file count, size, expiry).
 */
export const useStoreSelection = (vectorStores) => {
  const [selected, setSelected] = useState(null);

  const select = useCallback(async (store) => {
    setSelected(store);
    try {
      const response = await vectorStoresAPI.get(store.id);
      if (response.data) setSelected(response.data);
    } catch (error) {
      console.error('Failed to fetch store details:', error);
    }
  }, []);

  // The first store once the list arrives, or again after the shown one was deleted.
  useEffect(() => {
    const stillListed = selected && vectorStores.some((store) => store.id === selected.id);
    if (stillListed) return;
    if (vectorStores.length > 0) select(vectorStores[0]);
    else if (selected) setSelected(null);
  }, [vectorStores, selected, select]);

  return { selected, select, setSelected };
};
