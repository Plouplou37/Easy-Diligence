import { useState } from 'react';
import { answersAPI } from '../../../services/api';
import toast from 'react-hot-toast';

export const useVersionHistory = (onAnswerUpdate) => {
  const [showVersionHistory, setShowVersionHistory] = useState({});
  const [versionHistory, setVersionHistory] = useState({});

  const toggleVersionHistory = async (answerId) => {
    setShowVersionHistory(prev => ({
      ...prev,
      [answerId]: !prev[answerId]
    }));

    if (!versionHistory[answerId]) {
      await fetchVersionHistory(answerId);
    }
  };

  const fetchVersionHistory = async (answerId) => {
    try {
      const response = await answersAPI.getHistory(answerId);
      setVersionHistory(prev => ({
        ...prev,
        [answerId]: response.data.versions || []
      }));
    } catch (error) {
      toast.error('Failed to load version history');
    }
  };

  const revertToVersion = async (answerId, version, onReload) => {
    if (!confirm(`Are you sure you want to revert to version ${version}? This will create a new version with the content from version ${version}.`)) {
      return;
    }

    try {
      await answersAPI.revertToVersion(answerId, version);
      await onReload();
      await fetchVersionHistory(answerId);
      toast.success(`Successfully reverted to version ${version}`);
    } catch (error) {
      toast.error('Failed to revert to version');
    }
  };

  return {
    showVersionHistory,
    versionHistory,
    toggleVersionHistory,
    fetchVersionHistory,
    revertToVersion
  };
};
