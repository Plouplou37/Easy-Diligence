import { api } from '@/shared/api';

// Running a DD type on a session: start, pause, resume.
export const processingAPI = {
  start: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/start`),
  resume: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/resume`),
  pause: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/pause`),
};
