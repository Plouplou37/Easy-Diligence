import {
  ClockIcon,
  DocumentIcon,
  ExclamationTriangleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { formatBytes } from '@/shared/lib/format';
import { LoadingSpinner, Button, emptyState, tableStyles } from '@/shared/ui';

// OpenAI listed the file but did not give its details: the backend sends
// `details_missing`, and does not cache that answer.
const MISSING_DETAILS = "OpenAI did not return this file's details. Refresh to ask again.";

/** The file's creation date (OpenAI gives seconds), or "—". */
const createdOn = file =>
  Number.isFinite(file.created_at) ? new Date(file.created_at * 1000).toLocaleDateString() : '—';

const FileList = ({ files, loading, error, onRemoveFile }) => {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  // The listing failed: the store may well hold files, so never "No files".
  if (error) {
    return (
      <div className={emptyState.wrapper}>
        <ExclamationTriangleIcon className={emptyState.icon} />
        <p className={emptyState.title}>The files could not be listed</p>
        <p className={emptyState.text}>{error}</p>
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
            <th className={tableStyles.th}>File</th>
            <th className={tableStyles.th}>Size</th>
            <th className={tableStyles.th}>Created</th>
            <th className={tableStyles.thRight}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, index) => (
            <tr key={file.id} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
              <td className={tableStyles.td}>
                <div className="flex items-center">
                  <DocumentIcon className="h-5 w-5 text-accent-blue mr-2 shrink-0" />
                  <div
                    className={`max-w-xs truncate text-sm font-medium ${
                      file.details_missing ? 'text-content-muted italic' : 'text-content'
                    }`}
                    title={
                      file.details_missing
                        ? `${MISSING_DETAILS} ID: ${file.id}`
                        : `${file.filename} · ID: ${file.id}`
                    }
                  >
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
                  {createdOn(file)}
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
