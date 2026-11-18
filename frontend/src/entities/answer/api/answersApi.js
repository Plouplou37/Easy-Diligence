import { api, multipart } from '@/shared/api';

export const answersAPI = {
  getBySession: (sessionId, params) => api.get(`/answers/session/${sessionId}`, { params }),
  update: (answerId, data) => api.put(`/answers/${answerId}`, data),
  updateStatus: (answerId, status) => api.patch(`/answers/${answerId}/status`, { status }),
  getHistory: (answerId) => api.get(`/answers/${answerId}/history`),
  revertToVersion: (answerId, version) => api.post(`/answers/${answerId}/revert`, { version }),
  // Answer the question again (a new version, to review). Optional guidance:
  // an instruction, a URL the model is told to consult, a document added to
  // the session's vector store and cited in the new answer's sources.
  regenerate: (answerId, { instruction, referenceUrl, file } = {}) => {
    const form = new FormData();
    if (instruction) form.append('instruction', instruction);
    if (referenceUrl) form.append('reference_url', referenceUrl);
    if (file) form.append('file', file);
    return api.post(`/answers/${answerId}/regenerate`, form, multipart);
  },
  // The session's PDF report.
  export: (sessionId) =>
    api.get(`/answers/session/${sessionId}/export`, { responseType: 'blob' }),
};
