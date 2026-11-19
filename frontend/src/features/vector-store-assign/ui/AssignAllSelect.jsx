import { useState } from 'react';

/** "Assign to all": one store for every DD type of the session. */
export const AssignAllSelect = ({ vectorStores, onAssign }) => {
  const [value, setValue] = useState('');
  if (vectorStores.length === 0) return null;

  const choose = async storeId => {
    setValue(storeId);
    if (storeId) {
      await onAssign(storeId);
      setValue('');
    }
  };

  return (
    <div className="flex items-center gap-3 flex-shrink-0">
      <span className="text-xs text-content-muted">Assign to all:</span>
      <select
        value={value}
        onChange={event => choose(event.target.value)}
        className="form-input px-3 py-1 text-xs"
      >
        <option value="">Select vector store...</option>
        {vectorStores.map(store => (
          <option key={store.id} value={store.id}>
            {store.name} ({store.file_count} files)
          </option>
        ))}
      </select>
    </div>
  );
};
