import { useState } from 'react';
import { answersAPI } from '@/entities/answer';
import toast from 'react-hot-toast';

// The fields the server sent back, without those it left out: merged into the
// answer on screen, an undefined value would wipe what was there.
const defined = fields =>
  Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined));

export const useAnswerEditor = (onAnswerUpdate, onAfterSave) => {
  const [editingAnswer, setEditingAnswer] = useState(null);
  const [editText, setEditText] = useState('');
  const [revisionNotes, setRevisionNotes] = useState('');
  const [editingSources, setEditingSources] = useState([]);
  const [newSource, setNewSource] = useState({ type: 'web', content: '' });
  const [saving, setSaving] = useState(false);

  const startEdit = (answer, parsedSources) => {
    setEditingAnswer(answer.id);
    setEditText(answer.text);
    setRevisionNotes('');
    setEditingSources(parsedSources);
    setNewSource({ type: 'web', content: '' });
  };

  const cancelEdit = () => {
    setEditingAnswer(null);
    setEditText('');
    setRevisionNotes('');
    setEditingSources([]);
    setNewSource({ type: 'web', content: '' });
  };

  const saveEdit = async answerId => {
    setSaving(true);
    try {
      const updatedSources = JSON.stringify(editingSources);

      const response = await answersAPI.update(answerId, {
        answer_text: editText,
        edit_reason: revisionNotes,
        sources: updatedSources,
      });

      // An edit is a new version, back to review: the status changes too.
      const updatedAnswer = response.data;
      onAnswerUpdate(answerId, {
        text: editText,
        answer_text: editText,
        sources: updatedSources,
        ...defined({
          version: updatedAnswer.version || updatedAnswer.current_version,
          status: updatedAnswer.status,
          editor_name: updatedAnswer.editor_name,
          edited_at: updatedAnswer.edited_at,
        }),
      });

      cancelEdit();
      toast.success('Answer updated successfully');

      if (onAfterSave) {
        onAfterSave(answerId);
      }
    } catch (error) {
      toast.error('Failed to update answer');
    } finally {
      setSaving(false);
    }
  };

  const addSource = () => {
    if (newSource.content.trim()) {
      const sourceToAdd = {
        ...newSource,
        id: Date.now(),
        user_added: true,
      };
      setEditingSources([...editingSources, sourceToAdd]);
      setNewSource({ type: 'web', content: '' });
    }
  };

  const removeSource = sourceIndex => {
    setEditingSources(editingSources.filter((_, index) => index !== sourceIndex));
  };

  return {
    editingAnswer,
    editText,
    setEditText,
    revisionNotes,
    setRevisionNotes,
    editingSources,
    newSource,
    setNewSource,
    saving,
    startEdit,
    cancelEdit,
    saveEdit,
    addSource,
    removeSource,
  };
};
