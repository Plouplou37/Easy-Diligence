import { ClockIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { expiryLevel, isStale, isUnknown, storeState } from '@/entities/vector-store';
import { formatBytes } from '@/shared/lib/format';
import { Badge, panel, sectionHeader, tableStyles } from '@/shared/ui';

/** The store's state, or how soon it expires. */
const StoreMarker = ({ store }) => {
  const state = storeState(store);
  if (state) {
    return (
      <Badge variant={state.tone} size="sm">
        {state.label}
      </Badge>
    );
  }
  const expiry = expiryLevel(store);
  const when = store.expires_at ? new Date(store.expires_at).toLocaleDateString() : '';
  if (expiry === 'imminent') {
    return (
      <span title={`Expires on ${when} unless used`}>
        <ExclamationTriangleIcon className="h-4 w-4 text-theme-error" />
      </span>
    );
  }
  if (expiry === 'soon') {
    return (
      <span title={`Expires on ${when} unless used`}>
        <ClockIcon className="h-4 w-4 text-theme-warning" />
      </span>
    );
  }
  return null;
};

const VectorStoreList = ({ stores, selectedStore, onSelectStore }) => (
  <div className={`${panel.base} w-1/3 flex flex-col overflow-hidden`}>
    <div className={`${panel.header} shrink-0`}>
      <div className={sectionHeader.wrapper}>
        <h3 className={sectionHeader.title}>Vector Stores</h3>
        <div className={sectionHeader.hairline} />
      </div>
    </div>

    <div className="flex-1 overflow-y-auto max-h-[calc(100vh-var(--navbar-spacing)-220px)]">
      <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
        <thead className={tableStyles.theadSticky}>
          <tr>
            <th className={tableStyles.th}>Name</th>
            <th className={tableStyles.thRight}>Files</th>
            <th className={tableStyles.thRight}>Size</th>
          </tr>
        </thead>
        <tbody>
          {stores.map((store, index) => {
            const isSelected = selectedStore?.id === store.id;
            // A store gone at OpenAI, or not described, has no figures: "0" would read as empty.
            const known = !isStale(store) && !isUnknown(store);
            return (
              <tr
                key={store.id}
                onClick={() => onSelectStore(store)}
                className={`${tableStyles.row} ${
                  isSelected ? tableStyles.rowSelected : tableStyles.rowAlt(index)
                } cursor-pointer`}
              >
                {/* max-w-0 + w-full: the name column takes the remaining width
                    and truncates instead of stretching the table. */}
                <td className={`${tableStyles.td} relative w-full max-w-0`}>
                  {isSelected && <span className="rail-accent" />}
                  <div className="flex items-center gap-2">
                    <span
                      className={`flex-1 min-w-0 truncate text-sm font-medium ${
                        isStale(store) ? 'text-content-muted line-through' : 'text-content'
                      }`}
                    >
                      {store.name}
                    </span>
                    <span className="flex items-center gap-1 shrink-0">
                      <StoreMarker store={store} />
                    </span>
                  </div>
                </td>
                <td className={`${tableStyles.tdRight} tabular-nums`}>
                  {known ? store.file_count : '—'}
                </td>
                <td className={`${tableStyles.tdRight} whitespace-nowrap tabular-nums`}>
                  {known ? formatBytes(store.total_bytes) : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);

export default VectorStoreList;
