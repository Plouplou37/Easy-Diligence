import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { DocumentArrowDownIcon, TrashIcon } from '@heroicons/react/24/outline';
import { answersAPI } from '@/entities/answer';
import { sessionAPI } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';
import { downloadBlob } from '@/shared/lib/format';
import { Button } from '@/shared/ui';

// A session can be deleted unless it is running or finished: the status
// derived from its runs (getSessionStatus), which the server checks too.
const UNDELETABLE = {
  in_progress: 'Cannot delete a session while one of its DD types is running',
  completed: 'Cannot delete a completed session',
};

/** The session's report as a PDF (the syntheses, then every answer). */
const usePdfExport = sessionId => {
  const [exporting, setExporting] = useState(false);

  const exportPdf = async () => {
    setExporting(true);
    try {
      const response = await answersAPI.export(sessionId);
      downloadBlob(response.data, `session-${sessionId}-DD_Report.pdf`);
    } catch {
      toast.error('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  return { exporting, exportPdf };
};

export const ExportPdfButton = ({ sessionId }) => {
  const { exporting, exportPdf } = usePdfExport(sessionId);
  return (
    <Button
      variant="primary"
      size="sm"
      icon={DocumentArrowDownIcon}
      onClick={exportPdf}
      loading={exporting}
    >
      Export PDF
    </Button>
  );
};

/**
 * Delete the session and everything in it, after confirmation. `status` is
 * the session's, derived from its runs (getOverallStatus).
 */
export const DeleteSessionButton = ({ session, sessionId, status }) => {
  const navigate = useNavigate();
  const confirm = useConfirm();
  const lockedBecause = UNDELETABLE[status];

  const remove = async () => {
    const confirmed = await confirm({
      title: 'Delete session',
      message:
        `Delete "${session.name}" for good?\n\n` +
        'Its answers and their history, its runs and its vector store ' +
        'assignments go with it. This cannot be undone.',
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return;
    try {
      await sessionAPI.delete(sessionId);
      toast.success('Session deleted successfully');
      navigate('/');
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to delete session'));
    }
  };

  return (
    <Button
      variant="danger"
      size="sm"
      icon={TrashIcon}
      onClick={remove}
      disabled={Boolean(lockedBecause)}
      title={lockedBecause || 'Delete session'}
    >
      Delete Session
    </Button>
  );
};
