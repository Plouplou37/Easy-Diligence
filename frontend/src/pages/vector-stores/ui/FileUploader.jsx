import React from 'react';
import { CloudArrowUpIcon, TrashIcon, CheckCircleIcon, XCircleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { formatBytes } from '@/shared/lib/format';
import { Button } from '@/shared/ui';

const FileUploader = ({ stagedFiles, onFileSelect, onRemoveFile, onConfirmUpload, uploading }) => {
  return (
    <div className="border-2 border-dashed border-border hover:border-accent-blue transition-colors rounded-lg p-6">
      <input
        type="file"
        multiple
        onChange={onFileSelect}
        className="hidden"
        id="file-upload"
      />
      <label
        htmlFor="file-upload"
        className="cursor-pointer flex flex-col items-center justify-center"
      >
        <CloudArrowUpIcon className="h-12 w-12 text-content-muted mb-2" />
        <span className="text-sm text-content-secondary">
          Click to select files or drag and drop
        </span>
        <span className="text-xs text-content-muted mt-1">
          PDF, TXT, MD, DOC, DOCX up to 10MB each
        </span>
      </label>

      {stagedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-content-secondary">
              Staged Files ({stagedFiles.length})
            </h4>
            <Button
              onClick={onConfirmUpload}
              disabled={uploading}
              loading={uploading}
              variant="success"
              size="sm"
            >
              Upload All
            </Button>
          </div>

          {stagedFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between p-2 form-surface"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-content truncate">
                  {file.name}
                </div>
                <div className="text-xs text-content-muted">
                  {formatBytes(file.size)}
                </div>
              </div>
              <div className="flex items-center space-x-2 ml-2">
                {file.status === 'pending' && (
                  <button
                    onClick={() => onRemoveFile(file.id)}
                    className="text-theme-error hover:opacity-80"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                )}
                {file.status === 'uploading' && (
                  <ArrowPathIcon className="h-4 w-4 text-accent-blue animate-spin" />
                )}
                {file.status === 'success' && (
                  <CheckCircleIcon className="h-4 w-4 text-theme-success" />
                )}
                {file.status === 'error' && (
                  <XCircleIcon className="h-4 w-4 text-theme-error" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileUploader;
