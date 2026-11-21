import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  DocumentArrowDownIcon,
  EllipsisHorizontalIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { answersAPI } from '@/entities/answer';
import { sessionAPI } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';
import { downloadBlob } from '@/shared/lib/format';
import { Button, menu } from '@/shared/ui';

// A session can be deleted unless it is running or finished: the status
// derived from its runs (getSessionStatus), which the server checks too.
const UNDELETABLE = {
  in_progress: 'It cannot be deleted while one of its questionnaires is running.',
  completed: 'A completed due diligence cannot be deleted.',
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

export const ExportPdfButton = ({
  sessionId,
  variant = 'secondary',
  size = 'md',
  disabled = false,
  title,
}) => {
  const { exporting, exportPdf } = usePdfExport(sessionId);
  return (
    <Button
      variant={variant}
      size={size}
      icon={DocumentArrowDownIcon}
      onClick={exportPdf}
      loading={exporting}
      disabled={disabled}
      title={title}
    >
      Export PDF
    </Button>
  );
};

/**
 * Delete the session and everything in it, after confirmation. `status` is
 * the session's, derived from its runs (getOverallStatus).
 */
const useSessionDelete = ({ session, sessionId, status }) => {
  const navigate = useNavigate();
  const confirm = useConfirm();

  const remove = async () => {
    const confirmed = await confirm({
      title: 'Delete the due diligence',
      message:
        `Delete "${session.name}" for good?\n\n` +
        'Its answers and their history, its runs and its document collection ' +
        'assignments go with it. This cannot be undone.',
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return;
    try {
      await sessionAPI.delete(sessionId);
      toast.success('Due diligence deleted');
      navigate('/');
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to delete the due diligence'));
    }
  };

  return { remove, lockedBecause: UNDELETABLE[status] };
};

/**
 * The rarer actions on a due diligence, behind a "more" button: its deletion.
 * `status` is the session's, derived from its runs (getOverallStatus).
 */
export const SessionMenu = ({ session, sessionId, status, size = 'md' }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const { remove, lockedBecause } = useSessionDelete({ session, sessionId, status });

  // A click outside or Escape closes it.
  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = event => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    const onKeyDown = event => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <Button
        variant="secondary"
        size={size}
        icon={EllipsisHorizontalIcon}
        onClick={() => setOpen(shown => !shown)}
        className={size === 'lg' ? 'h-11 w-11' : 'h-10 w-10'}
        aria-label="More actions"
        aria-haspopup="menu"
        aria-expanded={open}
        title="More actions"
      />
      {open && (
        <div
          role="menu"
          aria-label="More actions"
          className={`absolute right-0 top-full z-30 mt-2 w-72 origin-top-right animate-scale-in py-1 ${menu.panel}`}
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              remove();
            }}
            disabled={Boolean(lockedBecause)}
            className={`${menu.itemDanger} disabled:pointer-events-none disabled:opacity-50`}
          >
            <TrashIcon className="h-4 w-4 shrink-0" />
            Delete this due diligence
          </button>
          {lockedBecause && (
            <p className="px-4 pb-2.5 text-xs text-content-muted">{lockedBecause}</p>
          )}
        </div>
      )}
    </div>
  );
};
