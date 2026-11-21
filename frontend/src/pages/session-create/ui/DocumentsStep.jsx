import { PlusIcon } from '@heroicons/react/24/outline';
import { expiryLevel, isUnknown, storeState } from '@/entities/vector-store';
import { ChoiceCard, FieldError, InsetBlock, plural } from '@/features/session-create';
import { formatBytes } from '@/shared/lib/format';
import { Badge, Button, Input, LoadingSpinner, field } from '@/shared/ui';
import { CollectionPanel } from './CollectionPanel';

/** The state of a collection, or how soon it expires. */
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
  if (!expiry) return null;
  return (
    <Badge variant={expiry === 'imminent' ? 'error' : 'warning'} size="sm">
      Expires soon
    </Badge>
  );
};

const describeStore = store => {
  if (isUnknown(store)) return 'Its figures are unknown for now';
  const parts = [plural(store.file_count, 'file'), formatBytes(store.total_bytes)];
  if (store.expires_at) {
    parts.push(`expires ${new Date(store.expires_at).toLocaleDateString()} unless used`);
  }
  return parts.join(' · ');
};

const ExistingCollections = ({ documents, error }) => {
  if (documents.loading && documents.usable.length === 0) {
    return <LoadingSpinner text="Loading your collections..." />;
  }
  return (
    <fieldset
      id="docs-existing"
      tabIndex={-1}
      aria-describedby={error ? 'docs-existing-error' : undefined}
      className="focus:outline-hidden"
    >
      <legend className={field.label}>Your document collections</legend>
      <div className="flex max-h-96 flex-col gap-2 overflow-y-auto p-0.5">
        {documents.usable.map(store => (
          <ChoiceCard
            key={store.id}
            id={`docs-store-${store.id}`}
            name="docs-store"
            checked={documents.existingId === store.id}
            onChange={() => documents.setExistingId(store.id)}
            title={store.name}
            hint={describeStore(store)}
            aside={<StoreMarker store={store} />}
          />
        ))}
      </div>
      <FieldError id="docs-existing-error">{error}</FieldError>
    </fieldset>
  );
};

const NewCollection = ({ documents, errors }) => {
  const { form, formErrors } = documents;
  const create = async () => {
    const invalid = await documents.createCollection();
    if (invalid) document.getElementById(invalid)?.focus();
  };
  // Enter creates the collection here, rather than submitting the step.
  const onEnter = event => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    create();
  };

  return (
    <InsetBlock title="A new collection">
      <div className="flex flex-wrap gap-4">
        <Input
          id="docs-new-name"
          className="flex-[2_1_15rem]"
          label="Name of the collection"
          required
          maxLength={255}
          value={form.name}
          onChange={event => documents.setFormField('name', event.target.value)}
          onKeyDown={onEnter}
          error={errors['docs-new-name'] || formErrors['docs-new-name']}
          placeholder="e.g. Example Asia Fund — 2026 documents"
          autoComplete="off"
        />
        <Input
          id="docs-new-days"
          className="flex-[1_1_10rem]"
          label="Expires after (days without use)"
          type="number"
          inputMode="numeric"
          min={1}
          max={365}
          required
          value={form.days}
          onChange={event => documents.setFormField('days', event.target.value)}
          onKeyDown={onEnter}
          error={formErrors['docs-new-days']}
        />
      </div>
      <p className={field.help}>
        OpenAI deletes the collection and its files after this many days without use; every run uses
        it again. You add the files once it is created.
      </p>
      <div>
        <Button
          type="button"
          variant="secondary"
          icon={PlusIcon}
          onClick={create}
          loading={documents.creating}
        >
          Create the collection
        </Button>
      </div>
    </InsetBlock>
  );
};

/**
 * Step 2: the documents the AI searches, optional. `documents`:
 * useDocumentsChoice. `fundName`: suggests the name of a new collection.
 */
export const DocumentsStep = ({ documents, fundName, errors }) => {
  const { mode, usable, loading } = documents;
  let existingHint = `${plural(usable.length, 'collection')} to choose from`;
  if (loading && usable.length === 0) existingHint = 'Loading your collections…';
  else if (usable.length === 0) existingHint = 'You have none yet';

  return (
    <div className="flex flex-col gap-5">
      <fieldset>
        <legend className="sr-only">Where the documents come from</legend>
        <div className="flex flex-col gap-2.5">
          <ChoiceCard
            id="docs-mode-existing"
            name="docs-mode"
            checked={mode === 'existing'}
            onChange={() => documents.choose('existing')}
            disabled={!loading && usable.length === 0 && mode !== 'existing'}
            title="Use a collection already uploaded"
            hint={existingHint}
          />
          <ChoiceCard
            id="docs-mode-new"
            name="docs-mode"
            checked={mode === 'new'}
            onChange={() =>
              documents.choose('new', fundName.trim() ? `${fundName.trim()} — documents` : '')
            }
            title="Upload new documents"
            hint="A new collection for this fund"
          />
          <ChoiceCard
            id="docs-mode-later"
            name="docs-mode"
            checked={mode === 'later'}
            onChange={() => documents.choose('later')}
            title="Add documents later"
            hint="Until then the AI searches the web only. You can assign a collection on the due diligence's page."
          />
        </div>
      </fieldset>

      {mode === 'existing' && (
        <ExistingCollections documents={documents} error={errors['docs-existing']} />
      )}
      {mode === 'new' && !documents.chosen && (
        <NewCollection documents={documents} errors={errors} />
      )}
      {documents.chosen && <CollectionPanel documents={documents} errors={errors} />}

      {mode !== 'later' && (
        <p className="text-xs text-content-muted">
          The files you upload are stored at OpenAI now, in the collection; the AI only searches
          them once you start the run.
        </p>
      )}
    </div>
  );
};
