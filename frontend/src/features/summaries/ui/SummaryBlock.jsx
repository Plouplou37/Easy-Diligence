import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { CheckIcon, PencilIcon, XMarkIcon } from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { summariesAPI } from '@/entities/summary';
import { Button } from '@/shared/ui';

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
      toast.success('Summary saved.');
      onSaved?.();
    } catch {
      toast.error('Failed to save the summary.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-lg border border-border p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.06em] text-content-secondary">
          {title}
        </h3>
        {!editing && (
          <Button onClick={() => setEditing(true)} variant="secondary" icon={PencilIcon}>
            Edit
          </Button>
        )}
      </div>

      {editing ? (
        <div className="space-y-3">
          <textarea
            value={text}
            onChange={event => setText(event.target.value)}
            rows={14}
            className="form-input w-full px-3 py-2 text-sm font-mono"
            aria-label={title}
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={save} variant="primary" icon={CheckIcon} loading={saving}>
              Save
            </Button>
            <Button
              onClick={() => setEditing(false)}
              variant="secondary"
              icon={XMarkIcon}
              disabled={saving}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="prose prose-sm max-w-none text-sm text-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {summary.summary_text || '_(empty)_'}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </section>
  );
};

export default SummaryBlock;
