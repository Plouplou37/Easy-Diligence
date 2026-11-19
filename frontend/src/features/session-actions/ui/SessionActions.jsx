import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ChevronDownIcon, DocumentArrowDownIcon, TrashIcon } from '@heroicons/react/24/outline';
import { answersAPI, exportAnswersToCSV } from '@/entities/answer';
import { sessionAPI } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';
import { downloadBlob } from '@/shared/lib/format';
import { Button, menu } from '@/shared/ui';

// A session can be deleted unless it is running or finished.
const UNDELETABLE = ['in_progress', 'completed'];

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

/** Export, as the session's PDF report or as a CSV table of `answers`. */
export const ExportMenu = ({ sessionId, answers }) => {
  const [open, setOpen] = useState(false);
  const { exporting, exportPdf } = usePdfExport(sessionId);

  const choose = action => () => {
    setOpen(false);
    action();
  };

  return (
    <div className="relative">
      <Button
        variant="primary"
        icon={DocumentArrowDownIcon}
        onClick={() => setOpen(shown => !shown)}
        loading={exporting}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {exporting ? 'Exporting…' : 'Export'}
        <ChevronDownIcon className="h-4 w-4" />
      </Button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div role="menu" className={`absolute right-0 mt-2 w-48 z-20 py-1 ${menu.panel}`}>
            <button role="menuitem" onClick={choose(exportPdf)} className={menu.item}>
              PDF report
            </button>
            <button
              role="menuitem"
              onClick={choose(() => exportAnswersToCSV(answers, sessionId))}
              className={menu.item}
            >
              CSV (table)
            </button>
          </div>
        </>
      )}
    </div>
  );
};

/** Delete the session and everything in it, after confirmation. */
export const DeleteSessionButton = ({ session, sessionId }) => {
  const navigate = useNavigate();
  const confirm = useConfirm();
  const locked = UNDELETABLE.includes(session.status);

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
      disabled={locked}
      title={locked ? `Cannot delete a session with status "${session.status}"` : 'Delete session'}
    >
      Delete Session
    </Button>
  );
};
