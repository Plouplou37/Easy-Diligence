import { useState } from 'react';
import toast from 'react-hot-toast';
import { isStale, vectorStoresAPI } from '@/entities/vector-store';
import { plural } from '@/features/session-create';
import { useFileManagement, useFileUpload, useVectorStores } from '@/features/vector-store-manage';
import { errorMessage } from '@/shared/api';

// models/vector_store.VectorStoreCreate
export const DEFAULT_EXPIRY_DAYS = 30;
const MAX_EXPIRY_DAYS = 365;

/**
 * The documents of the new due diligence: none for now ('later'), a collection
 * already uploaded ('existing'), or a new one created and filled here ('new').
 * The collection is assigned to the due diligence once it exists
 * (features/session-create, useCreateSession).
 */
export const useDocumentsChoice = () => {
  const stores = useVectorStores();
  const [mode, setMode] = useState('later');
  const [existingId, setExistingId] = useState('');
  // The collection created here, as the creation returned it.
  const [created, setCreated] = useState(null);
  const [form, setForm] = useState({ name: '', days: String(DEFAULT_EXPIRY_DAYS) });
  const [formErrors, setFormErrors] = useState({});
  const [creating, setCreating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // A store gone at OpenAI cannot be searched any more: it is not offered.
  const usable = stores.vectorStores.filter(store => !isStale(store));
  let chosenId = '';
  if (mode === 'existing') chosenId = existingId;
  if (mode === 'new') chosenId = created?.id || '';
  // The listed store has OpenAI's figures; the created one, until the list has it.
  const chosen = chosenId
    ? usable.find(store => store.id === chosenId) || (created?.id === chosenId ? created : null)
    : null;

  const refreshStore = async () => {
    if (chosen) await stores.refreshSingleStore(chosen.id);
  };
  const files = useFileManagement(chosen, refreshStore);
  const upload = useFileUpload(chosen, async () => {
    await refreshStore();
    await files.loadFiles();
  });

  const refresh = async () => {
    setRefreshing(true);
    try {
      await refreshStore();
      await files.loadFiles();
    } finally {
      setRefreshing(false);
    }
  };

  /** `suggestedName`: the name a new collection starts with. */
  const choose = (next, suggestedName) => {
    setMode(next);
    if (next === 'new' && !form.name && suggestedName) {
      setForm(previous => ({ ...previous, name: suggestedName }));
    }
  };

  const setFormField = (key, value) => {
    setForm(previous => ({ ...previous, [key]: value }));
    setFormErrors(previous => ({ ...previous, [`docs-new-${key}`]: undefined }));
  };

  /** Create the new collection. Resolves to the id of a field to fix, or null. */
  const createCollection = async () => {
    const name = form.name.trim();
    const days = Number(form.days);
    const errors = {};
    if (!name) errors['docs-new-name'] = 'Name the collection.';
    if (!Number.isInteger(days) || days < 1 || days > MAX_EXPIRY_DAYS) {
      errors['docs-new-days'] = `A whole number of days, from 1 to ${MAX_EXPIRY_DAYS}.`;
    }
    setFormErrors(errors);
    const invalid = Object.keys(errors)[0];
    if (invalid) return invalid;

    setCreating(true);
    try {
      const { data } = await vectorStoresAPI.create({ name, expires_after_days: days });
      setCreated(data);
      toast.success('Document collection created');
      stores.loadVectorStores();
    } catch (error) {
      toast.error(errorMessage(error, 'The document collection could not be created'));
    } finally {
      setCreating(false);
    }
    return null;
  };

  // The files the AI would search, as far as they are known.
  let fileCount = null;
  if (chosen && !files.filesLoading && !files.filesError) fileCount = files.files.length;
  else if (chosen && Number.isFinite(chosen.file_count)) fileCount = chosen.file_count;

  /** What blocks the step, keyed by the id of the element to fix. */
  const errors = () => {
    if (mode === 'later') return {};
    if (mode === 'existing' && !chosen) {
      return { 'docs-existing': 'Choose a collection, or add the documents later.' };
    }
    if (mode === 'new' && !chosen) {
      return { 'docs-new-name': 'Create the collection first, or add the documents later.' };
    }
    if (upload.uploadLoading) return { 'docs-upload': 'Wait for the upload to finish.' };
    const pending = upload.stagedFiles.filter(file => file.status === 'pending').length;
    if (pending > 0) {
      return {
        'docs-upload': `${plural(pending, 'file')} not uploaded yet: upload or remove ${
          pending === 1 ? 'it' : 'them'
        }.`,
      };
    }
    // An empty collection would have the AI told to search documents that are not there.
    if (!files.filesLoading && !files.filesError && files.files.length === 0) {
      return {
        'docs-choose':
          "This collection holds no file yet: add the fund's documents, or add them later.",
      };
    }
    return {};
  };

  return {
    loading: stores.loading,
    usable,
    mode,
    choose,
    existingId,
    setExistingId,
    created,
    form,
    setFormField,
    formErrors,
    creating,
    createCollection,
    chosen,
    fileCount,
    files,
    upload,
    refresh,
    refreshing,
    errors,
  };
};
