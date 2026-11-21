import { useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { ArrowUpTrayIcon, DocumentTextIcon, PencilSquareIcon } from '@heroicons/react/24/outline';
import { AiBadge, Button, FieldLabel, Input, Modal, modalStyles } from '@/shared/ui';
import { IMPORT_EXTENSIONS, nameFromFile } from '../lib/ddTypeDefaults';

const MODES = [
  {
    id: 'manual',
    icon: PencilSquareIcon,
    title: 'Start empty',
    text: 'Then add its sections and questions one by one.',
  },
  {
    id: 'import',
    icon: ArrowUpTrayIcon,
    title: 'Import a file',
    text: 'Excel, CSV or JSON: its sections and questions are read from it.',
  },
];

// The JSON shape services/file_parser.py reads.
const JSON_EXAMPLE = `[
  {
    "section": "Fund identity",
    "description": "Optional: what the section covers",
    "questions": [
      "When was the fund launched?",
      { "text": "Who is the depositary?", "context_prompt": "Prospectus" }
    ]
  }
]`;

/** A step's title, numbered when the form has several. */
const Step = ({ number, children }) => (
  <legend className="mb-3 flex items-center gap-2 text-sm font-semibold text-content">
    {number && (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-surface-hover text-xs tabular-nums text-content-secondary">
        {number}
      </span>
    )}
    {children}
  </legend>
);

/** How the import reads each format (services/file_parser.py). */
const FormatGuide = () => (
  <details className="form-surface px-4 py-3 text-sm">
    <summary className="cursor-pointer font-medium text-content">
      What the file should look like
    </summary>
    <div className="mt-3 space-y-4 text-content-secondary">
      <div>
        <p className="font-medium text-content">Excel (.xlsx, .xls) or CSV (.csv)</p>
        <ul className="mt-1 list-disc space-y-0.5 pl-5">
          <li>The first row is a header: it is skipped.</li>
          <li>Column A: the name of a section, which starts that section.</li>
          <li>Column B: one question per row, in the section above it.</li>
        </ul>
      </div>
      <div>
        <p className="font-medium text-content">JSON (.json)</p>
        <p className="mt-1">
          A list of sections. A question is a text, or an object with its “text” and, if you wish,
          “context_prompt” (where to look) and “ref” (your own reference, kept as its code).
        </p>
        <pre className="mt-2 overflow-x-auto rounded-md border border-border bg-surface p-3 font-mono text-xs leading-relaxed text-content-secondary">
          {JSON_EXAMPLE}
        </pre>
      </div>
      <p>Otherwise, the codes (A, A.01…) are given automatically.</p>
    </div>
  </details>
);

/**
 * Create a questionnaire (empty, or from a file), or edit one. `ddType`: the
 * one edited, or null for a new one. `onSave(values)` resolves to true once
 * saved, which closes the window.
 */
export const DdTypeFormModal = ({ ddType, onSave, onClose }) => {
  const isNew = !ddType;
  const fileInput = useRef(null);
  const [mode, setMode] = useState('manual');
  const [name, setName] = useState(ddType?.name || '');
  const [description, setDescription] = useState(ddType?.description || '');
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const importing = isNew && mode === 'import';

  const chooseFile = event => {
    const chosen = event.target.files[0];
    if (!chosen) return;
    const extension = `.${chosen.name.split('.').pop().toLowerCase()}`;
    if (!IMPORT_EXTENSIONS.includes(extension)) {
      toast.error(`Please choose an Excel, CSV or JSON file (${IMPORT_EXTENSIONS.join(', ')})`);
      event.target.value = '';
      return;
    }
    setFile(chosen);
    if (!name) setName(nameFromFile(chosen.name));
  };

  const submit = async event => {
    event.preventDefault();
    setSaving(true);
    const saved = await onSave({ name, description, file: importing ? file : null });
    setSaving(false);
    if (saved) onClose();
  };

  let submitLabel = 'Save changes';
  if (isNew) submitLabel = importing ? 'Import questionnaire' : 'Create questionnaire';
  // The steps are numbered only for a new questionnaire; the file comes before
  // the name, which is guessed from it.
  const detailsStep = isNew ? (importing ? 3 : 2) : null;

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isNew ? 'New questionnaire' : 'Edit questionnaire'}
      size="md"
    >
      <form onSubmit={submit}>
        <div className="space-y-6">
          {isNew && (
            <fieldset>
              <Step number={1}>How to start</Step>
              <div className="grid gap-3 sm:grid-cols-2">
                {MODES.map(({ id, icon: Icon, title, text }) => {
                  const checked = mode === id;
                  return (
                    <label
                      key={id}
                      className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors ${
                        checked
                          ? 'border-primary bg-primary-dark'
                          : 'border-border-hover bg-surface-bg hover:border-content-muted'
                      }`}
                    >
                      <input
                        type="radio"
                        name="dd-type-mode"
                        value={id}
                        checked={checked}
                        onChange={() => setMode(id)}
                        className="mt-1"
                      />
                      <span className="min-w-0">
                        <span className="flex items-center gap-1.5 text-sm font-semibold text-content">
                          <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                          {title}
                        </span>
                        <span className="mt-0.5 block text-xs text-content-secondary">{text}</span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          )}

          {importing && (
            <fieldset className="space-y-3">
              <Step number={2}>The file</Step>
              <input
                ref={fileInput}
                type="file"
                accept={IMPORT_EXTENSIONS.join(',')}
                onChange={chooseFile}
                className="hidden"
                tabIndex={-1}
                aria-hidden="true"
              />
              {file ? (
                <div className="flex items-center gap-3 rounded-lg border border-border bg-surface-bg py-2 pl-3 pr-2">
                  <DocumentTextIcon
                    className="h-5 w-5 shrink-0 text-content-muted"
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-content" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-xs tabular-nums text-content-muted">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <Button type="button" variant="ghost" onClick={() => fileInput.current?.click()}>
                    Change
                  </Button>
                </div>
              ) : (
                <div className="rounded-lg border-2 border-dashed border-border-hover px-4 py-6 text-center">
                  <p className="text-sm text-content-secondary">
                    Excel (.xlsx, .xls), CSV (.csv) or JSON (.json)
                  </p>
                  <Button
                    type="button"
                    variant="secondary"
                    icon={ArrowUpTrayIcon}
                    className="mt-3"
                    onClick={() => fileInput.current?.click()}
                  >
                    Choose a file
                  </Button>
                </div>
              )}
              <FormatGuide />
            </fieldset>
          )}

          <fieldset className="space-y-4">
            {isNew && <Step number={detailsStep}>Name and description</Step>}

            {/* The code is internal and fixed: shown for reference only. */}
            {!isNew && (
              <Input
                label="Code"
                value={ddType.code}
                disabled
                readOnly
                helperText="Fixed: it identifies the questionnaire."
              />
            )}

            <div>
              <FieldLabel htmlFor="dd-type-name" required aside={<AiBadge />}>
                Name
              </FieldLabel>
              <Input
                id="dd-type-name"
                required
                value={name}
                onChange={event => setName(event.target.value)}
                placeholder="Operational due diligence"
                helperText="The AI reads it when it writes the synthesis."
              />
            </div>

            <div>
              <FieldLabel
                htmlFor="dd-type-description"
                aside={<span className="text-xs text-content-muted">Not sent to the AI</span>}
              >
                Description
              </FieldLabel>
              <textarea
                id="dd-type-description"
                value={description}
                onChange={event => setDescription(event.target.value)}
                rows={3}
                className="form-input w-full px-3 py-2 text-sm"
                placeholder="What this questionnaire covers, for your team"
              />
            </div>
          </fieldset>
        </div>

        <div className={`${modalStyles.footer} -mx-5 -mb-4 mt-6`}>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={saving}
            disabled={!name.trim() || (importing && !file)}
          >
            {submitLabel}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
