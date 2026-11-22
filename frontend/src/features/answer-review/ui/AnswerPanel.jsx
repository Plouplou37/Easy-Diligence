import { useMemo } from 'react';
import {
  ArrowPathRoundedSquareIcon,
  ArrowUturnLeftIcon,
  CheckIcon,
  ClockIcon,
  PencilIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { getSourceContent, parseSourcesFromString } from '@/entities/answer';
import { useConfirm } from '@/shared/lib/confirm';
import { Badge, Button, Input } from '@/shared/ui';
import AnswerMarkdown from './AnswerMarkdown';
import SourcesList from './SourcesList';
import SourcesManager from './SourcesManager';
import VersionHistory from './VersionHistory';

/** Tokens and processing time are technical: kept in the tooltip. */
const AnsweredOn = ({ answer }) => {
  if (!answer.created_at) return null;
  const detail = [
    answer.tokens_used ? `Tokens: ${answer.tokens_used.toLocaleString()}` : null,
    answer.processing_time ? `Processing time: ${Math.round(answer.processing_time)} ms` : null,
  ]
    .filter(Boolean)
    .join(' · ');
  return (
    <p className="text-xs text-content-muted tabular-nums" title={detail || undefined}>
      Answered {new Date(answer.created_at).toLocaleString()}
    </p>
  );
};

/** The answer being edited: its text (markdown source), the reason, its sources. */
const AnswerEditor = ({ answer, editor }) => (
  <div className="space-y-3">
    {/* Monospace, like the synthesis editor: this is markdown source, and
        pipe tables are unreadable in a proportional font. */}
    <textarea
      value={editor.editText}
      onChange={event => editor.setEditText(event.target.value)}
      rows={14}
      className="form-input w-full px-3 py-2 text-sm font-mono"
      placeholder="Edit the answer..."
      aria-label="Answer"
    />
    <Input
      value={editor.revisionNotes}
      onChange={event => editor.setRevisionNotes(event.target.value)}
      placeholder="Reason for the change (optional)"
      aria-label="Reason for the change"
    />
    <SourcesManager
      editingSources={editor.editingSources}
      newSource={editor.newSource}
      setNewSource={editor.setNewSource}
      onAddSource={editor.addSource}
      onRemoveSource={editor.removeSource}
    />
    <div className="flex flex-wrap gap-2">
      <Button
        onClick={() => editor.saveEdit(answer.id)}
        variant="primary"
        icon={CheckIcon}
        loading={editor.saving}
      >
        Save
      </Button>
      <Button
        onClick={editor.cancelEdit}
        variant="secondary"
        icon={XMarkIcon}
        disabled={editor.saving}
      >
        Cancel
      </Button>
    </div>
  </div>
);

/**
 * One answer under review: what can be done with it (approve, edit, versions,
 * regenerate), its text, its sources. `review` comes from useAnswerReview.
 */
const AnswerPanel = ({ answer, review }) => {
  const confirm = useConfirm();
  const { editor, history, regeneration } = review;
  const sources = useMemo(() => parseSourcesFromString(answer.sources), [answer.sources]);
  const shownSources = sources.filter(source => getSourceContent(source) !== null).length;
  const isEditing = editor.editingAnswer === answer.id;
  const showHistory = Boolean(history.showVersionHistory[answer.id]);
  const approved = answer.status === 'approved';
  const isRegenerating = regeneration.regeneratingId === answer.id;

  const startEdit = async () => {
    // One answer is edited at a time: starting here drops the other draft.
    if (editor.editingAnswer && editor.editingAnswer !== answer.id) {
      const confirmed = await confirm({
        title: 'Discard the other edit',
        message:
          'Another answer is being edited and not saved yet. Discard its changes and edit this one?',
        confirmLabel: 'Discard and edit',
        danger: true,
      });
      if (!confirmed) return;
    }
    editor.startEdit(answer, sources);
  };

  if (isEditing) return <AnswerEditor answer={answer} editor={editor} />;

  return (
    <div className="space-y-5">
      {answer.status === 'failed' && (
        <p className="alert alert-error">
          The AI could not answer this question. Resume the run to try again, or regenerate this
          answer.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Button
          variant={approved ? 'secondary' : 'success'}
          icon={approved ? ArrowUturnLeftIcon : CheckIcon}
          onClick={() => review.toggleStatus(answer)}
          loading={review.statusPending === answer.id}
        >
          {approved ? 'Back to review' : 'Approve'}
        </Button>
        <Button variant="secondary" icon={PencilIcon} onClick={startEdit}>
          Edit
        </Button>
        <Button
          variant="secondary"
          icon={ClockIcon}
          onClick={() => history.toggleVersionHistory(answer.id)}
          aria-expanded={showHistory}
        >
          {showHistory ? 'Hide versions' : 'Versions'}
        </Button>
        <Button
          variant="secondary"
          icon={ArrowPathRoundedSquareIcon}
          onClick={() => regeneration.open(answer.id)}
          disabled={isRegenerating}
        >
          {isRegenerating ? 'Regenerating…' : 'Regenerate…'}
        </Button>
      </div>

      {showHistory && (
        <section aria-label="Versions" className="form-surface p-3">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-content">
            <ClockIcon className="h-4 w-4 text-content-muted" />
            Versions
            <Badge variant="info">Current: v{answer.version}</Badge>
          </h3>
          <VersionHistory
            answerId={answer.id}
            versions={history.versionHistory[answer.id]}
            onRevert={review.revert}
          />
        </section>
      )}

      {answer.text ? (
        <AnswerMarkdown>{answer.text}</AnswerMarkdown>
      ) : (
        <p className="text-sm text-content-muted">This answer has no text.</p>
      )}

      <section aria-label="Sources">
        <h3 className="eyebrow mb-2">
          Sources{shownSources > 0 && <span className="tabular-nums"> ({shownSources})</span>}
        </h3>
        {shownSources > 0 ? (
          <SourcesList sources={sources} />
        ) : (
          <p className="text-sm text-content-muted">No source cited.</p>
        )}
      </section>

      <AnsweredOn answer={answer} />
    </div>
  );
};

export default AnswerPanel;
