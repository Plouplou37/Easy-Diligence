import { useId, useState } from 'react';
import { isUnknown } from '@/entities/vector-store';

/** "6 files", or "files unknown" when OpenAI could not describe the store. */
const fileCount = store => (isUnknown(store) ? 'files unknown' : `${store.file_count} files`);

/**
 * A labelled list of the document collections (vector stores) to pick one
 * from: `onChoose(storeId)` runs on the pick, then the list resets. Nothing is
 * shown when there is no collection to pick.
 */
export const StoreSelect = ({ label, vectorStores, onChoose, disabled = false }) => {
  const id = useId();
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  if (vectorStores.length === 0) return null;

  const choose = async storeId => {
    setValue(storeId);
    if (!storeId) return;
    setBusy(true);
    try {
      await onChoose(storeId);
    } finally {
      setBusy(false);
      setValue('');
    }
  };

  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-content-secondary">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={event => choose(event.target.value)}
        disabled={disabled || busy}
        className="form-input h-10 w-full py-0 text-sm"
      >
        <option value="">Choose a document collection…</option>
        {vectorStores.map(store => (
          <option key={store.id} value={store.id}>
            {store.name} ({fileCount(store)})
          </option>
        ))}
      </select>
    </div>
  );
};
