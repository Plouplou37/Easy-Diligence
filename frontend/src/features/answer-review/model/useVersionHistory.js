import { useState } from 'react';
import toast from 'react-hot-toast';
import { answersAPI } from '@/entities/answer';
import { useConfirm } from '@/shared/lib/confirm';

/** The versions of each answer, loaded when first shown, and the revert. */
export const useVersionHistory = () => {
  const confirm = useConfirm();
  const [showVersionHistory, setShowVersionHistory] = useState({});
  const [versionHistory, setVersionHistory] = useState({});

  const fetchVersionHistory = async (answerId) => {
    try {
      const response = await answersAPI.getHistory(answerId);
      setVersionHistory((previous) => ({ ...previous, [answerId]: response.data.versions || [] }));
    } catch {
      toast.error('Failed to load version history');
    }
  };

  const toggleVersionHistory = async (answerId) => {
    setShowVersionHistory((previous) => ({ ...previous, [answerId]: !previous[answerId] }));
    if (!versionHistory[answerId]) {
      await fetchVersionHistory(answerId);
    }
  };

  const revertToVersion = async (answerId, version, onReload) => {
    const confirmed = await confirm({
      title: 'Revert answer',
      message:
        `Revert to version ${version}? A new version is created with its content; ` +
        'the current one stays in the history.',
      confirmLabel: 'Revert',
    });
    if (!confirmed) return;
    try {
      await answersAPI.revertToVersion(answerId, version);
      await onReload();
      await fetchVersionHistory(answerId);
      toast.success(`Reverted to version ${version}`);
    } catch {
      toast.error('Failed to revert to version');
    }
  };

  return { showVersionHistory, versionHistory, toggleVersionHistory, fetchVersionHistory, revertToVersion };
};
