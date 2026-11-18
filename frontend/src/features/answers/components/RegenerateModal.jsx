import React, { useState } from 'react';
import { ArrowPathRoundedSquareIcon, PaperClipIcon, XMarkIcon } from '@heroicons/react/24/outline';
import Modal from '../../../components/Modal';
import { Button, field } from '../../../components/ui';

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

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0] || null;
    if (selected && selected.size > MAX_SIZE) {
      setError('Le fichier dépasse 50 Mo.');
      e.target.value = '';
      return;
    }
    setError('');
    setFile(selected);
  };

  const handleSubmit = async () => {
    const url = referenceUrl.trim();
    if (url && !/^https?:\/\//i.test(url)) {
      setError('Le lien doit commencer par http:// ou https://');
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
    <Modal isOpen={isOpen} onClose={handleClose} title="Régénérer la réponse" size="md">
      <div className="space-y-4">
        <p className="text-sm text-content-muted">
          Tous les champs sont optionnels. Sans rien remplir, la réponse est simplement
          régénérée comme avant.
        </p>

        <div>
          <label className={field.label}>
            Consigne (optionnel)
          </label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={4}
            disabled={loading}
            placeholder="Ex. : concentre-toi sur les frais de gestion et cite les chiffres exacts."
            className="form-input w-full px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className={field.label}>
            Lien de référence (optionnel)
          </label>
          <input
            type="url"
            value={referenceUrl}
            onChange={(e) => setReferenceUrl(e.target.value)}
            disabled={loading}
            placeholder="https://exemple.com/page"
            className="form-input w-full px-3 py-2 text-sm"
          />
          <p className={field.help}>Consulté par l'IA via la recherche web.</p>
        </div>

        <div>
          <label className={field.label}>
            Fichier joint (optionnel)
          </label>
          {file ? (
            <div className="flex items-center justify-between form-surface px-3 py-2 text-sm">
              <span className="flex items-center text-content-secondary truncate">
                <PaperClipIcon className="h-4 w-4 mr-2 flex-shrink-0" />
                <span className="truncate">{file.name}</span>
              </span>
              <button
                type="button"
                onClick={() => setFile(null)}
                disabled={loading}
                className="ml-2 text-content-muted hover:text-content transition-colors"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <input
              type="file"
              accept={ACCEPTED}
              onChange={handleFileChange}
              disabled={loading}
              className="block w-full text-sm text-content-secondary file:mr-3 file:rounded-md file:border-0 file:bg-accent-blue/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent-blue hover:file:bg-accent-blue/20"
            />
          )}
          <p className={field.help}>
            Ajouté aux documents de la session et aux sources de la réponse (PDF, Word, Excel, CSV, TXT — max 50 Mo).
          </p>
        </div>

        {error && <p className="text-sm text-theme-error">{error}</p>}

        <div className="flex justify-end space-x-2 pt-2">
          <Button onClick={handleClose} variant="secondary" disabled={loading}>
            Annuler
          </Button>
          <Button
            onClick={handleSubmit}
            variant="primary"
            icon={ArrowPathRoundedSquareIcon}
            disabled={loading}
          >
            {loading ? 'Régénération…' : 'Régénérer'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default RegenerateModal;
