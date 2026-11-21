import { expiryLevel, isStale, isUnknown, storeState } from '@/entities/vector-store';
import { formatBytes } from '@/shared/lib/format';
import { Badge, panel } from '@/shared/ui';

const DAY_MS = 24 * 60 * 60 * 1000;

const fileCount = count => `${count} file${count === 1 ? '' : 's'}`;

/** The collection's state, or how soon it expires; nothing when all is well. */
const StoreMarker = ({ store }) => {
  const state = storeState(store);
  if (state) {
    return (
      <Badge variant={state.tone} size="sm">
        {state.label}
      </Badge>
    );
  }
  const level = expiryLevel(store);
  if (!level) return null;
  const expires = new Date(store.expires_at);
  const days = Math.max(0, Math.ceil((expires - Date.now()) / DAY_MS));
  const label = days === 0 ? 'Expires today' : `Expires in ${days} day${days === 1 ? '' : 's'}`;
  return (
    <span title={`Expires on ${expires.toLocaleDateString()} unless a due diligence uses it`}>
      <Badge variant={level === 'imminent' ? 'error' : 'warning'} size="sm">
        {label}
      </Badge>
    </span>
  );
};

/** What the line under the name says: the figures, or why there are none. */
const figures = store => {
  if (isStale(store)) return 'No documents left';
  if (isUnknown(store)) return 'Figures unknown';
  return `${fileCount(store.file_count)} · ${formatBytes(store.total_bytes)}`;
};

/** The document collections, the selected one highlighted. */
const VectorStoreList = ({ stores, selectedStore, onSelectStore }) => (
  <nav
    aria-label="Document collections"
    className={`${panel.base} min-w-0 flex-[1_1_280px] overflow-hidden lg:sticky lg:top-(--navbar-spacing)`}
  >
    <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
      <h2 className="eyebrow">Collections</h2>
      <span className="text-xs tabular-nums text-content-muted">{stores.length}</span>
    </div>

    <ul className="max-h-80 space-y-1 overflow-y-auto p-2 lg:max-h-[calc(100vh-var(--navbar-spacing)-8rem)]">
      {stores.map(store => {
        const selected = selectedStore?.id === store.id;
        return (
          <li key={store.id}>
            <button
              type="button"
              onClick={() => onSelectStore(store)}
              aria-current={selected ? 'true' : undefined}
              className={`flex min-h-11 w-full flex-col gap-1 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                selected
                  ? 'border-primary bg-primary-dark'
                  : 'border-transparent hover:bg-surface-hover'
              }`}
            >
              <span
                className={`w-full truncate text-sm font-medium ${
                  isStale(store) ? 'text-content-muted line-through' : 'text-content'
                }`}
                title={store.name}
              >
                {store.name}
              </span>
              <span className="flex w-full flex-wrap items-center justify-between gap-x-2 gap-y-1">
                <span className="text-xs tabular-nums text-content-secondary">
                  {figures(store)}
                </span>
                <StoreMarker store={store} />
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  </nav>
);

export default VectorStoreList;
