import { useState } from 'react';
import { ArrowPathRoundedSquareIcon, PaperClipIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { Modal } from '@/shared/ui';
import { Button, field } from '@/shared/ui';

// Accepted document types (mirrors DocumentUpload), 50 Mo max.
const ACCEPTED = '.pdf,.doc,.docx,.txt,.csv,.xls,.xlsx';
const MAX_SIZE = 50 * 1024 * 1024;

const RegenerateModal = ({ isOpen, onClose, onSubmit, loading }) => {
  const [instruction, setInstruction] = useState('');
  const [referenceUrl, setReferenceUrl] = useState('');
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');

  const reset = () => {
    setInstruction('');
    setReferenceUrl('');
    setFile(null);
    setError('');
  };

  const handleClose = () => {
    if (loading) return;
    reset();
    onClose();
  };

  const handleFileChange = e => {
    const selected = e.target.files?.[0] || null;
    if (selected && selected.size > MAX_SIZE) {
      setError('The file is larger than 50 MB.');
      e.target.value = '';
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
    await onSubmit({
      instruction: instruction.trim() || undefined,
      referenceUrl: url || undefined,
      file: file || undefined,
    });
    reset();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Regenerate the answer" size="md">
      <div className="space-y-4">
        <p className="text-sm text-content-muted">
          Every field is optional. With none filled in, the answer is simply generated again.
        </p>

        <div>
          <label htmlFor="regenerate-instruction" className={field.label}>
            Instruction (optional)
          </label>
          <textarea
            id="regenerate-instruction"
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            rows={4}
            disabled={loading}
            placeholder="E.g. focus on the management fees and quote the exact figures."
            className="form-input w-full px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label htmlFor="regenerate-link" className={field.label}>
            Reference link (optional)
          </label>
          <input
            id="regenerate-link"
            type="url"
            value={referenceUrl}
            onChange={e => setReferenceUrl(e.target.value)}
            disabled={loading}
            placeholder="https://example.com/page"
            className="form-input w-full px-3 py-2 text-sm"
          />
          <p className={field.help}>The AI reads it through its web search.</p>
        </div>

        <div>
          <label htmlFor="regenerate-file" className={field.label}>
            Attached file (optional)
          </label>
          {file ? (
            <div className="flex items-center justify-between form-surface px-3 py-2 text-sm">
              <span className="flex items-center text-content-secondary truncate">
                <PaperClipIcon className="h-4 w-4 mr-2 shrink-0" />
                <span className="truncate">{file.name}</span>
              </span>
              <button
                type="button"
                onClick={() => setFile(null)}
                disabled={loading}
                className="ml-2 text-content-muted hover:text-content transition-colors"
                aria-label="Remove the file"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <input
              id="regenerate-file"
              type="file"
              accept={ACCEPTED}
              onChange={handleFileChange}
              disabled={loading}
              className="block w-full text-sm text-content-secondary file:mr-3 file:rounded-md file:border-0 file:bg-accent-blue/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent-blue hover:file:bg-accent-blue/20"
            />
          )}
          <p className={field.help}>
            Added to the session’s documents and to the answer’s sources (PDF, Word, Excel, CSV,
            TXT, up to 50 MB).
          </p>
        </div>

        {error && <p className="text-sm text-theme-error">{error}</p>}

        <div className="flex justify-end space-x-2 pt-2">
          <Button onClick={handleClose} variant="secondary" disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            variant="primary"
            icon={ArrowPathRoundedSquareIcon}
            disabled={loading}
          >
            {loading ? 'Regenerating…' : 'Regenerate'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default RegenerateModal;
