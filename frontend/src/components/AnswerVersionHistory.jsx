import React, { useState, useEffect } from 'react';
import {
  ClockIcon,
  DocumentTextIcon,
  ArrowUturnLeftIcon,
  EyeIcon,
  EyeSlashIcon,
  UserIcon,
  LinkIcon
} from '@heroicons/react/24/outline';
import { answersAPI } from '../services/api';
import toast from 'react-hot-toast';
import SourcesList from '../features/answers/components/SourcesList';

const AnswerVersionHistory = ({ answerId }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [reverting, setReverting] = useState(false);

  useEffect(() => {
    if (answerId && showHistory) {
      loadHistory();
    }
  }, [answerId, showHistory]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await answersAPI.getHistory(answerId);
      setHistory(response.data);
    } catch (error) {
      toast.error('Failed to load answer history');
    } finally {
      setLoading(false);
    }
  };

  const handleRevertToVersion = async (version) => {
    if (!confirm(`Are you sure you want to revert to version ${version}? This will create a new version with the content from version ${version}.`)) {
      return;
    }

    try {
      setReverting(true);
      await answersAPI.revertToVersion(answerId, version);
      toast.success(`Successfully reverted to version ${version}`);
      loadHistory();
      window.location.reload();
    } catch (error) {
      toast.error('Failed to revert to version');
    } finally {
      setReverting(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const truncateText = (text, maxLength = 150) => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="flex items-center text-sm text-gray-600 hover:text-gray-800"
        >
          {showHistory ? (
            <EyeSlashIcon className="h-4 w-4 mr-1" />
          ) : (
            <EyeIcon className="h-4 w-4 mr-1" />
          )}
          {showHistory ? 'Hide' : 'Show'} Version History
          {history.length > 0 && ` (${history.length} versions)`}
        </button>
      </div>

      {showHistory && (
        <div className="border rounded-lg bg-gray-50">
          {loading ? (
            <div className="p-4 text-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Loading history...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="p-4 text-center text-gray-500 text-sm">
              No version history available
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {history.map((version, index) => (
                <div key={version.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <DocumentTextIcon className="h-4 w-4 text-gray-500" />
                        <span className="font-medium text-sm">
                          Version {version.version}
                          {index === 0 && (
                            <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                              Current
                            </span>
                          )}
                        </span>
                        <ClockIcon className="h-4 w-4 text-gray-400" />
                        <span className="text-xs text-gray-500">
                          {formatDate(version.created_at)}
                        </span>
                      </div>

                      {version.edit_reason && (
                        <div className="mb-2">
                          <span className="text-xs font-medium text-gray-700">Reason: </span>
                          <span className="text-xs text-gray-600">{version.edit_reason}</span>
                        </div>
                      )}

                      <div className="text-sm text-gray-700 bg-white p-3 rounded border">
                        {truncateText(version.content)}
                        {version.content && version.content.length > 150 && (
                          <button className="text-blue-600 text-xs ml-2 hover:underline">
                            View Full
                          </button>
                        )}
                      </div>

                      {version.sources && (
                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                          <div className="flex items-center mb-2">
                            <LinkIcon className="w-3 h-3 mr-1 text-gray-500 dark:text-gray-400" />
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                              Sources Referenced
                            </span>
                          </div>
                          <SourcesList sources={version.sources} compact={true} />
                        </div>
                      )}

                      {version.editor_name && (
                        <div className="flex items-center mt-2 text-xs text-gray-500">
                          <UserIcon className="h-3 w-3 mr-1" />
                          Edited by: {version.editor_name}
                        </div>
                      )}
                    </div>

                    {index > 0 && (
                      <button
                        onClick={() => handleRevertToVersion(version.version)}
                        disabled={reverting}
                        className="ml-4 px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 disabled:opacity-50 flex items-center"
                      >
                        <ArrowUturnLeftIcon className="h-3 w-3 mr-1" />
                        {reverting ? 'Reverting...' : 'Revert'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnswerVersionHistory;