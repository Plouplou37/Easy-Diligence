import { useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { answersAPI } from '@/entities/answer';

/** The versions of each answer, loaded when first shown, and the revert. */
export const useVersionHistory = () => {
  const [showVersionHistory, setShowVersionHistory] = useState({});
  const [versionHistory, setVersionHistory] = useState({});

  // Stable: a page may load the versions from an effect.
  const fetchVersionHistory = useCallback(async answerId => {
    try {
      const response = await answersAPI.getHistory(answerId);
      setVersionHistory(previous => ({ ...previous, [answerId]: response.data.versions || [] }));
    } catch {
      toast.error('Failed to load version history');
    }
  }, []);

  const toggleVersionHistory = async answerId => {
    setShowVersionHistory(previous => ({ ...previous, [answerId]: !previous[answerId] }));
    if (!versionHistory[answerId]) {
      await fetchVersionHistory(answerId);
    }
  };

  // No confirmation: a revert creates a new version and loses nothing, so it
  // is undone by reverting again. Confirmations are kept for what cannot be undone.
  const revertToVersion = async (answerId, version, onReload) => {
    try {
      await answersAPI.revertToVersion(answerId, version);
      await onReload();
      await fetchVersionHistory(answerId);
      toast.success(`Reverted to version ${version}. The previous text stays in the history.`);
    } catch {
      toast.error('Failed to revert to version');
    }
  };

  return {
    showVersionHistory,
    versionHistory,
    toggleVersionHistory,
    fetchVersionHistory,
    revertToVersion,
  };
};
