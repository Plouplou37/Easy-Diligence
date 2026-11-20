import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { summariesAPI } from '@/entities/summary';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';

// A batch still in OpenAI's hands. Mirrors PENDING_BATCH_STATUSES in
// engine/summarizer.py: while the status is one of these, nothing is stored yet.
export const PENDING_BATCH_STATUSES = ['validating', 'in_progress', 'finalizing', 'cancelling'];

const BATCH_POLL_MS = 15000;

/**
 * The synthesis of one DD type of a session: its summaries, their generation
 * (now, or through OpenAI's Batch API at half price) and the batch's state.
 */
export const useSynthesis = (sessionId, ddTypeCode) => {
  const confirm = useConfirm();
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  // The OpenAI batch, when one was launched for this DD type.
  const [batch, setBatch] = useState(null);
  const [cancellingBatch, setCancellingBatch] = useState(false);
  const previousBatchStatus = useRef(null);

  const load = useCallback(async () => {
    if (!ddTypeCode) return;
    setLoading(true);
    try {
      const response = await summariesAPI.list(sessionId, ddTypeCode);
      setSummaries(Array.isArray(response.data) ? response.data : []);
    } catch {
      toast.error('Failed to load the synthesis.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, ddTypeCode]);

  useEffect(() => {
    load();
  }, [load]);

  // Polling the status is also what collects a finished batch server-side:
  // it is what turns results into summaries, not merely a read.
  const refreshBatch = useCallback(async () => {
    if (!ddTypeCode) return null;
    try {
      const response = await summariesAPI.batchStatus(sessionId, ddTypeCode);
      const state = response.data || null;
      setBatch(state && state.status !== 'none' ? state : null);

      // Announce the transition only, not the steady state: a batch collected
      // during an earlier visit must not toast on every mount.
      const was = previousBatchStatus.current;
      previousBatchStatus.current = state?.status || null;
      if (state?.status === 'collected' && PENDING_BATCH_STATUSES.includes(was)) {
        await load();
        toast.success('Synthesis generated (batch).');
      }
      return state;
    } catch (error) {
      console.error('Failed to read batch status:', error);
      return null;
    }
  }, [sessionId, ddTypeCode, load]);

  // Pick up a batch left running by a previous visit: it survives a reload,
  // and a page refresh is otherwise the only thing that would advance it.
  useEffect(() => {
    previousBatchStatus.current = null;
    refreshBatch();
  }, [refreshBatch]);

  const batchPending = Boolean(batch) && PENDING_BATCH_STATUSES.includes(batch.status);

  // Keep polling while OpenAI still has the job.
  useEffect(() => {
    if (!batchPending) return undefined;
    const interval = setInterval(refreshBatch, BATCH_POLL_MS);
    return () => clearInterval(interval);
  }, [batchPending, refreshBatch]);

  const generate = async () => {
    setGenerating(true);
    try {
      await summariesAPI.generate(sessionId, ddTypeCode);
      await load();
      toast.success('Synthesis generated.');
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to generate the synthesis.'));
    } finally {
      setGenerating(false);
    }
  };

  const generateBatch = async () => {
    setGenerating(true);
    try {
      const response = await summariesAPI.generateBatch(sessionId, ddTypeCode);
      setBatch(response.data || null);
      previousBatchStatus.current = response.data?.status || null;
      toast.success('Section summaries queued (batch).');
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to queue the batch.'));
    } finally {
      setGenerating(false);
    }
  };

  const cancelBatch = async () => {
    // Irreversible: the requests not yet processed are dropped for good.
    const confirmed = await confirm({
      title: 'Cancel the batch',
      message: 'Cancel the batch? The section summaries not produced yet will be dropped.',
      confirmLabel: 'Cancel the batch',
      cancelLabel: 'Keep it running',
      danger: true,
    });
    if (!confirmed) return;
    setCancellingBatch(true);
    try {
      const response = await summariesAPI.cancelBatch(sessionId, ddTypeCode);
      const state = response.data || null;
      if (state && PENDING_BATCH_STATUSES.includes(state.status)) {
        // 'cancelling': keep polling until OpenAI confirms 'cancelled'.
        setBatch(state);
        previousBatchStatus.current = state.status;
        toast.success('Cancellation requested.');
      } else {
        // Already over on OpenAI's side. Let the regular status call record it,
        // and collect the results if it turns out to have completed.
        previousBatchStatus.current = 'in_progress';
        await refreshBatch();
        toast(state?.message || 'The batch had already finished.');
      }
    } catch (error) {
      toast.error(errorMessage(error, 'Failed to cancel the batch.'));
    } finally {
      setCancellingBatch(false);
    }
  };

  return {
    summaries,
    loading,
    load,
    generating,
    generate,
    generateBatch,
    batch,
    batchPending,
    cancellingBatch,
    cancelBatch,
  };
};
