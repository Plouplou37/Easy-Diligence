import React from 'react';
import { ClockIcon, ArrowPathRoundedSquareIcon, UserIcon } from '@heroicons/react/24/outline';
import { Badge } from '../../../components/ui';

const VersionHistory = ({ answerId, versions, onRevert }) => {
  if (!versions || versions.length === 0) {
    return (
      <div className="text-sm text-content-muted italic">
        No version history available
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {versions.map((version) => (
        <div
          key={version.version}
          className="form-surface p-3"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-medium text-content-secondary">
                Version {version.version}
              </span>
              {version.is_current && (
                <Badge variant="success">
                  Current
                </Badge>
              )}
            </div>
            {!version.is_current && (
              <button
                onClick={() => onRevert(answerId, version.version)}
                className="flex items-center text-xs text-link"
              >
                <ArrowPathRoundedSquareIcon className="w-3 h-3 mr-1" />
                Revert
              </button>
            )}
          </div>

          <div className="text-xs text-content-secondary space-y-1">
            {version.edited_by && (
              <div className="flex items-center">
                <UserIcon className="w-3 h-3 mr-1" />
                Edited by: {version.edited_by}
              </div>
            )}
            {version.created_at && (
              <div className="flex items-center">
                <ClockIcon className="w-3 h-3 mr-1" />
                {new Date(version.created_at).toLocaleString()}
              </div>
            )}
            {version.edit_reason && (
              <div className="mt-1 text-content-secondary">
                Reason: {version.edit_reason}
              </div>
            )}
          </div>

          <div className="mt-2 text-sm text-content bg-surface p-2 rounded max-h-32 overflow-y-auto">
            {version.content}
          </div>
        </div>
      ))}
    </div>
  );
};

export default VersionHistory;
