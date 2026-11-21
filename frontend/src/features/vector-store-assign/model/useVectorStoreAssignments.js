import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { isStale, vectorStoresAPI } from '@/entities/vector-store';

// The assignment as the page shows it: the name comes with it, so a
// colleague's store -- usable by the engine, absent from the user's own list --
// still shows.
const describe = assignment => ({
  id: assignment.vector_store_id,
  name: assignment.vector_store_name,
});

/**
 * The vector stores of a session: the user's stores to pick from, the store
 * assigned to each DD type, and the one assigned to the whole session (which
 * every DD type without its own uses). A store gone at OpenAI is not offered,
 * but an assigned one still shows, with its state. `loaded`: the first load
 * is done.
 */
export const useVectorStoreAssignments = ({ sessionId, ddTypes }) => {
  const [allStores, setAllStores] = useState([]);
  const [byDdType, setByDdType] = useState({});
  const [sessionWide, setSessionWide] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    const [stores, assignments] = await Promise.allSettled([
      vectorStoresAPI.list(),
      vectorStoresAPI.getSessionAssignments(sessionId),
    ]);
    setAllStores(
      stores.status === 'fulfilled' && Array.isArray(stores.value.data) ? stores.value.data : []
    );
    const list =
      assignments.status === 'fulfilled' ? assignments.value.data?.assignments || [] : [];
    const map = {};
    list
      .filter(item => item.dd_type_code)
      .forEach(item => {
        map[item.dd_type_code] = describe(item);
      });
    const whole = list.find(item => !item.dd_type_code);
    setByDdType(map);
    setSessionWide(whole ? describe(whole) : null);
    setLoaded(true);
  }, [sessionId]);

  const ddTypeOf = code => ddTypes.find(ddType => ddType.code === code);
  const storeName = storeId => allStores.find(store => store.id === storeId)?.name;

  /** The store a DD type's run searches: its own, or the session's. */
  const assignedTo = code => {
    const assigned = byDdType[code] || sessionWide;
    if (!assigned) return undefined;
    return allStores.find(store => store.id === assigned.id) || assigned;
  };

  /** Whose store that is: the DD type's own ('own'), the session's ('session'), or none. */
  const scopeOf = code => {
    if (byDdType[code]) return 'own';
    return sessionWide ? 'session' : null;
  };

  const assign = async (code, storeId) => {
    const ddType = ddTypeOf(code);
    try {
      await vectorStoresAPI.assignToSession(storeId, sessionId, { dd_type_id: ddType?.id });
      setByDdType(previous => ({ ...previous, [code]: { id: storeId, name: storeName(storeId) } }));
      toast.success(`Documents assigned to ${ddType?.name || code}`);
    } catch {
      toast.error('Failed to assign the documents');
    }
  };

  const assignAll = async (storeId, codes) => {
    const name = storeName(storeId) || 'The document collection';
    try {
      await Promise.all(
        codes.map(code =>
          vectorStoresAPI.assignToSession(storeId, sessionId, { dd_type_id: ddTypeOf(code)?.id })
        )
      );
      setByDdType(previous => ({
        ...previous,
        ...Object.fromEntries(codes.map(code => [code, { id: storeId, name }])),
      }));
      toast.success(`${name} assigned to every questionnaire`);
    } catch {
      toast.error('Failed to assign the documents to every questionnaire');
    }
  };

  const remove = async code => {
    const own = byDdType[code];
    try {
      // The page may be showing the session-wide store: that assignment has no
      // DD type, and removing it takes the documents from every type.
      await vectorStoresAPI.removeFromSession(
        (own || sessionWide)?.id,
        sessionId,
        own ? code : null
      );
      if (own) {
        setByDdType(({ [code]: _removed, ...rest }) => rest);
        toast.success(`Documents removed from ${ddTypeOf(code)?.name || code}`);
      } else {
        setSessionWide(null);
        toast.success('Documents removed from every questionnaire of this due diligence');
      }
    } catch {
      toast.error('Failed to remove the documents');
    }
  };

  const vectorStores = allStores.filter(store => !isStale(store));

  return { vectorStores, loaded, load, assignedTo, scopeOf, assign, assignAll, remove };
};
