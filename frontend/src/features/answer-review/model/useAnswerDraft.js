import { useCallback, useState } from 'react';
import { answersAPI } from '@/entities/answer';

const NO_SOURCE = { type: 'web', content: '' };

/**
 * The draft of one answer: its text (markdown), the reason for the change and
 * its sources, the user's own among them. `reset(answer, parsedSources)`
 * starts it from an answer and remembers that start, so `changed` says
 * whether the text or the sources differ from it. `save(answerId)` stores the
 * draft as a new version: it resolves to `{ text, sources, saved }` (what was
 * sent, and the answer the server sent back) and rejects when the request
 * fails.
 */
export const useAnswerDraft = () => {
  const [text, setText] = useState('');
  const [reason, setReason] = useState('');
  const [sources, setSources] = useState([]);
  const [newSource, setNewSource] = useState(NO_SOURCE);
  const [start, setStart] = useState({ text: '', sources: '[]' });
  const [saving, setSaving] = useState(false);

  const reset = useCallback((answer, parsedSources = []) => {
    const startText = answer?.text || '';
    setText(startText);
    setReason('');
    setSources(parsedSources);
    setNewSource(NO_SOURCE);
    setStart({ text: startText, sources: JSON.stringify(parsedSources) });
  }, []);

  const save = async answerId => {
    setSaving(true);
    try {
      const sentSources = JSON.stringify(sources);
      const response = await answersAPI.update(answerId, {
        answer_text: text,
        edit_reason: reason,
        sources: sentSources,
      });
      return { text, sources: sentSources, saved: response.data || {} };
    } finally {
      setSaving(false);
    }
  };

  const addSource = () => {
    if (!newSource.content.trim()) return;
    setSources([...sources, { ...newSource, id: Date.now(), user_added: true }]);
    setNewSource(NO_SOURCE);
  };

  const removeSource = sourceIndex => {
    setSources(sources.filter((_, index) => index !== sourceIndex));
  };

  return {
    text,
    setText,
    reason,
    setReason,
    sources,
    newSource,
    setNewSource,
    addSource,
    removeSource,
    changed: text !== start.text || JSON.stringify(sources) !== start.sources,
    saving,
    reset,
    save,
  };
};
