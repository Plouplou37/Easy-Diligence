import { Link } from 'react-router-dom';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { expiryLevel, isStale, isUnknown, storeProblem, storeState } from '@/entities/vector-store';
import { StoreSelect } from '@/features/vector-store-assign';
import { AiBadge, Badge, Button } from '@/shared/ui';

const filesOf = store => {
  if (isUnknown(store)) return 'Files unknown';
  if (typeof store.file_count !== 'number') return null;
  return `${store.file_count} file${store.file_count === 1 ? '' : 's'}`;
};

const expiryOf = store => {
  if (!store.expires_at || isStale(store)) return null;
  return `expires ${new Date(store.expires_at).toLocaleDateString()} if unused`;
};

/**
 * The document collection the selected questionnaire's run searches: its own
 * or the whole due diligence's, its state, and the means to change it
 * (`stores`: useVectorStoreAssignments). `lockReason`: why it cannot be
 * changed now, if it cannot.
 */
export const DocumentsCard = ({ ddType, ddTypeCodes, stores, lockReason, progress }) => {
  const code = ddType.code;
  const assigned = stores.assignedTo(code);
  const scope = stores.scopeOf(code);
  const stale = Boolean(assigned) && isStale(assigned);
  const problem = assigned ? storeProblem(assigned) : null;
  const expiring = assigned ? expiryLevel(assigned) : null;
  const multiple = ddTypeCodes.length > 1;
  const counted = progress?.answers_counted || 0;
  const details = assigned ? [filesOf(assigned), expiryOf(assigned)].filter(Boolean) : [];

  return (
    <section
      aria-labelledby="documents-card-title"
      className="space-y-3 rounded-xl border border-border bg-surface p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id="documents-card-title" className="eyebrow">
          Documents
        </h2>
        {stores.loaded &&
          (stale ? (
            <Badge variant="error" icon={ExclamationTriangleIcon}>
              {storeState(assigned).label}
            </Badge>
          ) : assigned ? (
            <AiBadge title="The AI searches these documents for every question.">
              Searched by the AI
            </AiBadge>
          ) : (
            <Badge variant="warning" icon={ExclamationTriangleIcon}>
              None assigned
            </Badge>
          ))}
      </div>

      {!stores.loaded ? (
        <div className="space-y-2" aria-hidden="true">
          <div className="h-4 w-3/4 animate-pulse rounded bg-surface-hover" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-surface-hover" />
        </div>
      ) : assigned ? (
        <div>
          <p className="font-semibold text-content wrap-break-word">{assigned.name}</p>
          {details.length > 0 && (
            <p
              className={`mt-0.5 text-xs tabular-nums ${expiring ? 'text-theme-warning' : 'text-content-secondary'}`}
            >
              {details.join(' · ')}
            </p>
          )}
          {(multiple || scope === 'session') && (
            <p className="mt-0.5 text-xs text-content-muted">
              {scope === 'session'
                ? 'For every questionnaire of this due diligence'
                : 'For this questionnaire'}
            </p>
          )}
          {problem && (
            <p className={`mt-2 text-xs ${stale ? 'text-theme-error' : 'text-theme-warning'}`}>
              {problem}
            </p>
          )}
          {counted > 0 && (
            <p className="mt-2 text-xs text-content-muted tabular-nums">
              Cited by {progress.answers_with_documents} of {counted} answers
            </p>
          )}
        </div>
      ) : (
        <p className="text-sm text-content-secondary">
          {stores.vectorStores.length > 0
            ? 'No document collection yet: without one, the AI answers from the web alone.'
            : 'You have no document collection to assign yet.'}
        </p>
      )}

      {stores.loaded &&
        (lockReason ? (
          <p className="text-xs text-content-muted">{lockReason}</p>
        ) : assigned ? (
          <Button variant="secondary" onClick={() => stores.remove(code)}>
            {scope === 'session' ? 'Remove from every questionnaire' : 'Remove'}
          </Button>
        ) : (
          <StoreSelect
            label="Assign a collection"
            vectorStores={stores.vectorStores}
            onChoose={storeId => stores.assign(code, storeId)}
          />
        ))}

      {stores.loaded && multiple && (
        <StoreSelect
          label="Use one collection for every questionnaire"
          vectorStores={stores.vectorStores}
          onChoose={storeId => stores.assignAll(storeId, ddTypeCodes)}
        />
      )}

      <Link to="/vector-stores" className="inline-flex min-h-10 items-center text-sm text-link">
        Manage documents
      </Link>
    </section>
  );
};
