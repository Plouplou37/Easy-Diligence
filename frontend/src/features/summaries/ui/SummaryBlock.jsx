import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { CheckIcon, PencilIcon, XMarkIcon } from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { summariesAPI } from '@/entities/summary';
import { Button, panel, sectionHeader } from '@/shared/ui';

/** One editable block: the global synthesis or a section summary. */
const SummaryBlock = ({ title, summary, onSaved }) => {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(summary.summary_text || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editing) setText(summary.summary_text || '');
  }, [summary.summary_text, editing]);

  const save = async () => {
    setSaving(true);
    try {
      await summariesAPI.update(summary.id, text);
      setEditing(false);
      toast.success('Résumé enregistré.');
      onSaved?.();
    } catch {
      toast.error('Échec de l’enregistrement.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`${panel.base} p-5`}>
      <div className="flex items-center justify-between gap-3 mb-3">
        <h3 className="text-fluid-sm font-medium text-content uppercase tracking-[0.18em]">{title}</h3>
        <div className={sectionHeader.hairline} />
        {!editing && (
          <Button onClick={() => setEditing(true)} variant="secondary" size="sm" icon={PencilIcon}>
            Éditer
          </Button>
        )}
      </div>

      {editing ? (
        <div className="space-y-3">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={14}
            className="form-input w-full px-3 py-2 text-sm font-mono"
            aria-label={title}
          />
          <div className="flex space-x-2">
            <Button onClick={save} variant="success" icon={CheckIcon} disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </Button>
            <Button onClick={() => setEditing(false)} variant="secondary" icon={XMarkIcon} disabled={saving}>
              Annuler
            </Button>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="prose prose-sm max-w-none text-sm text-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary.summary_text || '_(vide)_'}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
};

export default SummaryBlock;
