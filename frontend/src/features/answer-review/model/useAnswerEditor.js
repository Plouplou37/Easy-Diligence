import { useState } from 'react';
import toast from 'react-hot-toast';
import { useAnswerDraft } from './useAnswerDraft';

// The fields the server sent back, without those it left out: merged into the
// answer on screen, an undefined value would wipe what was there.
const defined = fields =>
  Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined));

/**
 * The answer edited in a list, one at a time (`editingAnswer`), with its
 * draft. onAnswerUpdate(answerId, changes): the saved edit, to show;
 * onAfterSave(answerId): called once it is saved.
 */
export const useAnswerEditor = (onAnswerUpdate, onAfterSave) => {
  const [editingAnswer, setEditingAnswer] = useState(null);
  const draft = useAnswerDraft();

  const startEdit = (answer, parsedSources) => {
    setEditingAnswer(answer.id);
    draft.reset(answer, parsedSources);
  };

  const cancelEdit = () => {
    setEditingAnswer(null);
    draft.reset(null, []);
  };

  const saveEdit = async answerId => {
    try {
      const { text, sources, saved } = await draft.save(answerId);

      // An edit is a new version, back to review: the status changes too.
      onAnswerUpdate(answerId, {
        text,
        answer_text: text,
        sources,
        ...defined({
          version: saved.version || saved.current_version,
          status: saved.status,
          editor_name: saved.editor_name,
          edited_at: saved.edited_at,
        }),
      });

      cancelEdit();
      toast.success('Answer updated successfully');
      onAfterSave?.(answerId);
    } catch {
      toast.error('Failed to update answer');
    }
  };

  return {
    editingAnswer,
    editText: draft.text,
    setEditText: draft.setText,
    revisionNotes: draft.reason,
    setRevisionNotes: draft.setReason,
    editingSources: draft.sources,
    newSource: draft.newSource,
    setNewSource: draft.setNewSource,
    saving: draft.saving,
    startEdit,
    cancelEdit,
    saveEdit,
    addSource: draft.addSource,
    removeSource: draft.removeSource,
  };
};
