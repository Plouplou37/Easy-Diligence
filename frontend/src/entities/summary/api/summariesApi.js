import { api } from '@/shared/api';

// Section summaries and the DD type synthesis.
export const summariesAPI = {
  // Written now, during the request.
  generate: (sessionId, ddType) =>
    api.post(`/summaries/session/${sessionId}/dd/${ddType}/generate`),
  // Through the OpenAI Batch API: half price, up to 24 h. Poll batchStatus,
  // which also stores the results once the batch is done.
  generateBatch: (sessionId, ddType) =>
    api.post(`/summaries/session/${sessionId}/dd/${ddType}/generate/batch`),
  batchStatus: (sessionId, ddType) => api.get(`/summaries/session/${sessionId}/dd/${ddType}/batch`),
  // Stop a batch still queued at OpenAI; requests already done stay billed.
  cancelBatch: (sessionId, ddType) =>
    api.post(`/summaries/session/${sessionId}/dd/${ddType}/batch/cancel`),
  list: (sessionId, ddType = null) =>
    api.get(`/summaries/session/${sessionId}`, { params: ddType ? { dd_type: ddType } : {} }),
  update: (summaryId, summaryText) =>
    api.put(`/summaries/${summaryId}`, { summary_text: summaryText }),
};
