import { ExclamationTriangleIcon, ClockIcon } from '@heroicons/react/24/outline';
import { formatBytes, getExpirationStatus } from '@/shared/lib/format';
import { panel, sectionHeader, tableStyles } from '@/shared/ui';

const VectorStoreList = ({ stores, selectedStore, onSelectStore }) => {
  return (
    <div className={`${panel.base} w-1/3 flex flex-col overflow-hidden`}>
      <div className={`${panel.header} flex-shrink-0`}>
        <div className={sectionHeader.wrapper}>
          <h3 className={sectionHeader.title}>Vector Stores</h3>
          <div className={sectionHeader.hairline} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[calc(100vh_-_var(--navbar-spacing)_-_220px)]">
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
              const expirationStatus = getExpirationStatus(store.expires_at);
              const isSelected = selectedStore?.id === store.id;

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
                      <span className="flex-1 min-w-0 truncate text-sm font-medium text-content">
                        {store.name}
                      </span>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {(expirationStatus === 'expired' || expirationStatus === 'critical') && (
                          <ExclamationTriangleIcon className="h-4 w-4 text-theme-error" />
                        )}
                        {expirationStatus === 'warning' && (
                          <ClockIcon className="h-4 w-4 text-theme-warning" />
                        )}
                      </div>
                    </div>
                  </td>
                  <td className={`${tableStyles.tdRight} tabular-nums`}>{store.file_count}</td>
                  <td className={`${tableStyles.tdRight} whitespace-nowrap tabular-nums`}>
                    {formatBytes(store.total_bytes)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default VectorStoreList;
