import { useState } from 'react';
import toast from 'react-hot-toast';
import { ArrowUpTrayIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { Button, Input, Modal, field, modalStyles, tabs } from '@/shared/ui';
import { IMPORT_EXTENSIONS, nameFromFile } from '../lib/ddTypeDefaults';

const MODES = [
  { id: 'manual', label: 'Manual Entry' },
  { id: 'import', label: 'Import from File', icon: ArrowUpTrayIcon },
];

/**
 * Create a DD type (by hand, or from a questionnaire file), or edit one.
 * `ddType`: the one edited, or null for a new one. `onSave(values)` resolves
 * to true once saved, which closes the window.
 */
export const DdTypeFormModal = ({ ddType, onSave, onClose }) => {
  const isNew = !ddType;
  const [mode, setMode] = useState('manual');
  const [name, setName] = useState(ddType?.name || '');
  const [description, setDescription] = useState(ddType?.description || '');
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const importing = isNew && mode === 'import';

  const chooseFile = (event) => {
    const chosen = event.target.files[0];
    if (!chosen) return;
    const extension = `.${chosen.name.split('.').pop().toLowerCase()}`;
    if (!IMPORT_EXTENSIONS.includes(extension)) {
      toast.error(`Please select a valid file format (${IMPORT_EXTENSIONS.join(', ')})`);
      event.target.value = '';
      return;
    }
    setFile(chosen);
    if (!name) setName(nameFromFile(chosen.name));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    const saved = await onSave({ name, description, file: importing ? file : null });
    setSaving(false);
    if (saved) onClose();
  };

  let submitLabel = 'Save Changes';
  if (isNew) submitLabel = importing ? 'Import DD Type' : 'Create DD Type';

  return (
    <Modal isOpen onClose={onClose} title={isNew ? 'Create New DD Type' : 'Edit DD Type'} size="md">
      <form onSubmit={submit} className="space-y-4">
        {isNew && (
          <div className={tabs.group} role="tablist">
            {MODES.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={mode === id}
                onClick={() => setMode(id)}
                className={`${tabs.tab} flex items-center ${mode === id ? tabs.active : tabs.inactive}`}
              >
                {Icon && <Icon className="w-4 h-4 mr-2" />}
                {label}
                {mode === id && <span className={tabs.indicator} />}
              </button>
            ))}
          </div>
        )}

        {/* The code is internal and fixed: shown for reference only. */}
        {!isNew && <Input label="Code (read-only)" value={ddType.code} disabled readOnly />}

        <Input
          label="Name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Technical Due Diligence"
        />

        <div>
          <label htmlFor="dd-type-description" className={field.label}>
            Description
          </label>
          <textarea
            id="dd-type-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            className="form-input w-full px-3 py-2 text-sm"
            placeholder="What this due diligence covers"
          />
        </div>

        {importing && (
          <div>
            <label htmlFor="dd-type-file" className={field.label}>
              Questionnaire file <span className="text-theme-error">*</span>
            </label>
            <input
              id="dd-type-file"
              type="file"
              accept={IMPORT_EXTENSIONS.join(',')}
              onChange={chooseFile}
              className="block w-full text-sm text-content-secondary file:mr-3 file:rounded-md file:border-0 file:bg-accent-blue/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent-blue file:cursor-pointer hover:file:bg-accent-blue/20"
            />
            <p className={field.help}>Supported formats: Excel (.xlsx, .xls), CSV (.csv), JSON (.json)</p>
            {file && (
              <div className="mt-3 p-3 form-surface flex items-center">
                <DocumentTextIcon className="w-5 h-5 text-content-muted mr-2" />
                <div>
                  <p className="text-sm text-content">{file.name}</p>
                  <p className="text-xs text-content-muted">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              </div>
            )}
          </div>
        )}

        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-4`}>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={saving} disabled={!name.trim() || (importing && !file)}>
            {submitLabel}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
