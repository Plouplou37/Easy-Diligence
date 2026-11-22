import { useId, useState } from 'react';
import { ArrowPathRoundedSquareIcon, PaperClipIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { AiBadge, Button, FieldLabel, Input, field } from '@/shared/ui';

// Accepted document types (mirrors DocumentUpload), 50 MB max.
const ACCEPTED = '.pdf,.doc,.docx,.txt,.csv,.xls,.xlsx';
const MAX_SIZE = 50 * 1024 * 1024;

/**
 * The optional guidance of a regeneration: an instruction and a link, both
 * read by the AI, and a document added to the session. In a dialog
 * (RegenerateModal) or inline (the answer window).
 *
 * onSubmit({ instruction, referenceUrl, file }): runs the regeneration; it
 * resolves to false when it failed, and the fields then keep what was typed.
 * onCancel, when given, adds a Cancel button. loading: a regeneration runs.
 */
const RegenerateForm = ({ onSubmit, onCancel, loading = false }) => {
  const id = useId();
  const [instruction, setInstruction] = useState('');
  const [referenceUrl, setReferenceUrl] = useState('');
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');

  const handleFileChange = event => {
    const selected = event.target.files?.[0] || null;
    if (selected && selected.size > MAX_SIZE) {
      setError('The file is larger than 50 MB.');
      event.target.value = '';
      return;
    }
    setError('');
    setFile(selected);
  };

  const handleSubmit = async () => {
    const url = referenceUrl.trim();
    if (url && !/^https?:\/\//i.test(url)) {
      setError('The link must start with http:// or https://');
      return;
    }
    setError('');
    const done = await onSubmit({
      instruction: instruction.trim() || undefined,
      referenceUrl: url || undefined,
      file: file || undefined,
    });
    if (done === false) return;
    setInstruction('');
    setReferenceUrl('');
    setFile(null);
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-content-muted">
        Every field is optional. With none filled in, the answer is simply generated again.
      </p>

      <div>
        <FieldLabel htmlFor={`${id}-instruction`} aside={<AiBadge />}>
          Instruction (optional)
        </FieldLabel>
        <textarea
          id={`${id}-instruction`}
          value={instruction}
          onChange={event => setInstruction(event.target.value)}
          rows={4}
          disabled={loading}
          placeholder="E.g. focus on the management fees and quote the exact figures."
          className="form-input w-full px-3 py-2 text-sm"
        />
      </div>

      <div>
        <FieldLabel htmlFor={`${id}-link`} aside={<AiBadge />}>
          Reference link (optional)
        </FieldLabel>
        <Input
          id={`${id}-link`}
          type="url"
          value={referenceUrl}
          onChange={event => setReferenceUrl(event.target.value)}
          disabled={loading}
          placeholder="https://example.com/page"
          helperText="The AI reads it through its web search."
        />
      </div>

      <div>
        <FieldLabel htmlFor={`${id}-file`} aside={<AiBadge>Searched by the AI</AiBadge>}>
          Attached file (optional)
        </FieldLabel>
        {file ? (
          <div className="flex items-center justify-between form-surface px-3 py-1 text-sm">
            <span className="flex min-w-0 items-center text-content-secondary">
              <PaperClipIcon className="mr-2 h-4 w-4 shrink-0" />
              <span className="truncate">{file.name}</span>
            </span>
            <button
              type="button"
              onClick={() => setFile(null)}
              disabled={loading}
              className="ml-2 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-content-muted transition-colors hover:bg-surface-hover hover:text-content disabled:opacity-50"
              aria-label="Remove the file"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <input
            id={`${id}-file`}
            type="file"
            accept={ACCEPTED}
            onChange={handleFileChange}
            disabled={loading}
            className="block w-full text-sm text-content-secondary file:mr-3 file:rounded-md file:border-0 file:bg-accent-blue/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent-blue hover:file:bg-accent-blue/20"
          />
        )}
        <p className={field.help}>
          Added to the session’s documents and to the answer’s sources (PDF, Word, Excel, CSV, TXT,
          up to 50 MB).
        </p>
      </div>

      {error && <p className="text-sm text-theme-error">{error}</p>}

      <div className="flex flex-wrap justify-end gap-2 pt-2">
        {onCancel && (
          <Button onClick={onCancel} variant="secondary" disabled={loading}>
            Cancel
          </Button>
        )}
        <Button
          onClick={handleSubmit}
          variant="primary"
          icon={ArrowPathRoundedSquareIcon}
          loading={loading}
        >
          {loading ? 'Regenerating…' : 'Regenerate'}
        </Button>
      </div>
    </div>
  );
};

export default RegenerateForm;
