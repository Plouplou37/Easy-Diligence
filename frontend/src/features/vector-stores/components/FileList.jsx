import React from 'react';
import { DocumentIcon, TrashIcon, ClockIcon } from '@heroicons/react/24/outline';
import { formatBytes } from '../utils/formatters';
import { LoadingSpinner, Button, emptyState, tableStyles } from '../../../components/ui';

const FileList = ({ files, loading, onRemoveFile }) => {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className={emptyState.wrapper}>
        <DocumentIcon className={emptyState.icon} />
        <p className={emptyState.title}>No files in this vector store</p>
      </div>
    );
  }

  return (
    <div className="h-full border border-border rounded-lg overflow-y-auto">
      <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
        <thead className={tableStyles.theadSticky}>
          <tr>
            <th className={tableStyles.th}>
              File
            </th>
            <th className={tableStyles.th}>
              Size
            </th>
            <th className={tableStyles.th}>
              Created
            </th>
            <th className={tableStyles.thRight}>
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, index) => (
            <tr key={file.id} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
              <td className={tableStyles.td}>
                <div className="flex items-center">
                  <DocumentIcon className="h-5 w-5 text-accent-blue mr-2 flex-shrink-0" />
                  <div className="max-w-xs truncate text-sm font-medium text-content" title={`${file.filename} · ID: ${file.id}`}>
                    {file.filename}
                  </div>
                </div>
              </td>
              <td className={`${tableStyles.td} whitespace-nowrap tabular-nums`}>
                {formatBytes(file.size_bytes)}
              </td>
              <td className={tableStyles.td}>
                <div className="flex items-center whitespace-nowrap text-content-secondary">
                  <ClockIcon className="h-4 w-4 mr-1 text-content-muted" />
                  {new Date(file.created_at * 1000).toLocaleDateString()}
                </div>
              </td>
              <td className={tableStyles.tdRight}>
                <div className="flex items-center justify-end space-x-2">
                  <Button
                    onClick={() => onRemoveFile(file.id)}
                    variant="danger"
                    size="sm"
                    icon={TrashIcon}
                    title="Remove file"
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default FileList;
