import { Link } from 'react-router-dom';
import { BookOpenIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { isStale, isUnknown, storeState } from '@/entities/vector-store';

/** "6 files", or "files unknown" when OpenAI could not describe the store. */
const fileCount = store => (isUnknown(store) ? 'files unknown' : `${store.file_count} files`);
import { getToneStyles } from '@/shared/lib/status';
import { Badge } from '@/shared/ui';

/**
 * The vector store the run searches, or a picker to assign one. Shown when
 * there is a store to pick from or one already assigned: an existing
 * assignment must not vanish because the list of stores failed to load.
 */
export const AssignedDocuments = ({ code, vectorStores, assigned, locked, onAssign, onRemove }) => {
  if (vectorStores.length === 0 && !assigned) return null;

  if (assigned) {
    // Gone at OpenAI: the run would search nothing, so say it where it is chosen.
    const stale = isStale(assigned);
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="eyebrow leading-4">Documents</span>
          {/* file_count is unknown when the store is only known through the
              assignment, or when OpenAI could not be reached. */}
          {stale ? (
            <Badge variant="error" icon={ExclamationTriangleIcon}>
              {storeState(assigned).label}
            </Badge>
          ) : (
            <span className="text-xs text-content-muted">
              {typeof assigned.file_count === 'number' ? fileCount(assigned) : 'assigned'}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2">
          <span
            className={`inline-flex items-center gap-1 min-w-0 px-2 py-0.5 rounded-xl border text-xs font-medium ${getToneStyles(stale ? 'error' : 'success').badge}`}
            title={
              stale
                ? 'This vector store is gone at OpenAI: its documents can no longer be searched. Remove it and assign another.'
                : undefined
            }
          >
            <BookOpenIcon className="w-3 h-3 shrink-0" />
            <span className="truncate">{assigned.name}</span>
          </span>
          {!locked && onRemove && (
            <button onClick={() => onRemove(code)} className="pill-action" data-variant="danger">
              Remove
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="eyebrow leading-4">Documents</span>
        <span className="flex items-center gap-2">
          <Link to="/vector-stores" className="text-xs text-link">
            Manage stores
          </Link>
          <Badge variant="warning" icon={ExclamationTriangleIcon}>
            None assigned
          </Badge>
        </span>
      </div>
      {!locked && onAssign ? (
        <select
          onChange={event => event.target.value && onAssign(code, event.target.value)}
          className="form-input w-full px-2 py-1 text-xs"
        >
          <option value="">Select vector store...</option>
          {vectorStores.map(store => (
            <option key={store.id} value={store.id}>
              {store.name} ({fileCount(store)})
            </option>
          ))}
        </select>
      ) : (
        locked && <span className="text-xs text-content-muted">Cannot change while processing</span>
      )}
    </div>
  );
};
