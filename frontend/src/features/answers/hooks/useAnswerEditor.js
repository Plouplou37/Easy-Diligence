import { useState } from 'react';
import { answersAPI } from '../../../services/api';
import toast from 'react-hot-toast';

export const useAnswerEditor = (onAnswerUpdate, onAfterSave) => {
  const [editingAnswer, setEditingAnswer] = useState(null);
  const [editText, setEditText] = useState('');
  const [revisionNotes, setRevisionNotes] = useState('');
  const [editingSources, setEditingSources] = useState([]);
  const [newSource, setNewSource] = useState({ type: 'web', content: '' });

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

  const saveEdit = async (answerId) => {
    try {
      const updatedSources = JSON.stringify(editingSources);

      const response = await answersAPI.update(answerId, {
        answer_text: editText,
        edit_reason: revisionNotes,
        sources: updatedSources
      });

      const updatedAnswer = response.data;
      onAnswerUpdate(answerId, {
        text: editText,
        sources: updatedSources,
        version: updatedAnswer.version || updatedAnswer.current_version
      });

      cancelEdit();
      toast.success('Answer updated successfully');

      if (onAfterSave) {
        onAfterSave(answerId);
      }
    } catch (error) {
      toast.error('Failed to update answer');
    }
  };

  const addSource = () => {
    if (newSource.content.trim()) {
      const sourceToAdd = {
        ...newSource,
        id: Date.now(),
        user_added: true
      };
      setEditingSources([...editingSources, sourceToAdd]);
      setNewSource({ type: 'web', content: '' });
    }
  };

  const removeSource = (sourceIndex) => {
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
    startEdit,
    cancelEdit,
    saveEdit,
    addSource,
    removeSource
  };
};
