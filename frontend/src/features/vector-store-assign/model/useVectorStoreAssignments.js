import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { vectorStoresAPI } from '@/entities/vector-store';

// The assignment as the cards show it: the name comes with it, so a
// colleague's store -- usable by the engine, absent from the user's own list --
// still shows.
const describe = (assignment) => ({
  id: assignment.vector_store_id,
  name: assignment.vector_store_name,
});

/**
 * The vector stores of a session: the user's stores to pick from, the store
 * assigned to each DD type, and the one assigned to the whole session (which
 * every DD type without its own uses).
 */
export const useVectorStoreAssignments = ({ sessionId, ddTypes }) => {
  const [vectorStores, setVectorStores] = useState([]);
  const [byDdType, setByDdType] = useState({});
  const [sessionWide, setSessionWide] = useState(null);

  const load = useCallback(async () => {
    const [stores, assignments] = await Promise.allSettled([
      vectorStoresAPI.list(),
      vectorStoresAPI.getSessionAssignments(sessionId),
    ]);
    setVectorStores(
      stores.status === 'fulfilled' && Array.isArray(stores.value.data) ? stores.value.data : []
    );
    const list = assignments.status === 'fulfilled' ? assignments.value.data?.assignments || [] : [];
    const map = {};
    list.filter((item) => item.dd_type_code).forEach((item) => {
      map[item.dd_type_code] = describe(item);
    });
    const whole = list.find((item) => !item.dd_type_code);
    setByDdType(map);
    setSessionWide(whole ? describe(whole) : null);
  }, [sessionId]);

  const ddTypeOf = (code) => ddTypes.find((ddType) => ddType.code === code);
  const storeName = (storeId) => vectorStores.find((store) => store.id === storeId)?.name;

  /** The store a DD type's run searches: its own, or the session's. */
  const assignedTo = (code) => {
    const assigned = byDdType[code] || sessionWide;
    if (!assigned) return undefined;
    return vectorStores.find((store) => store.id === assigned.id) || assigned;
  };

  const assign = async (code, storeId) => {
    const ddType = ddTypeOf(code);
    try {
      await vectorStoresAPI.assignToSession(storeId, sessionId, { dd_type_id: ddType?.id });
      setByDdType((previous) => ({ ...previous, [code]: { id: storeId, name: storeName(storeId) } }));
      toast.success(`Vector store assigned to ${ddType?.name || code}`);
    } catch {
      toast.error('Failed to assign vector store');
    }
  };

  const assignAll = async (storeId, codes) => {
    const name = storeName(storeId) || 'vector store';
    try {
      await Promise.all(
        codes.map((code) =>
          vectorStoresAPI.assignToSession(storeId, sessionId, { dd_type_id: ddTypeOf(code)?.id })
        )
      );
      setByDdType((previous) => ({
        ...previous,
        ...Object.fromEntries(codes.map((code) => [code, { id: storeId, name }])),
      }));
      toast.success(`${name} assigned to all DD types`);
    } catch {
      toast.error('Failed to bulk assign vector store');
    }
  };

  const remove = async (code) => {
    const own = byDdType[code];
    try {
      // The card may be showing the session-wide store: that assignment has no
      // DD type, and removing it takes the documents from every type.
      await vectorStoresAPI.removeFromSession((own || sessionWide)?.id, sessionId, own ? code : null);
      if (own) {
        setByDdType(({ [code]: _removed, ...rest }) => rest);
        toast.success(`Vector store removed from ${ddTypeOf(code)?.name || code}`);
      } else {
        setSessionWide(null);
        toast.success('Vector store removed from all DD types of this session');
      }
    } catch {
      toast.error('Failed to remove vector store assignment');
    }
  };

  return { vectorStores, load, assignedTo, assign, assignAll, remove };
};
