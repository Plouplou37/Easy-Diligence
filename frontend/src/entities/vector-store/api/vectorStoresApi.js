import { api, multipart } from '@/shared/api';

export const vectorStoresAPI = {
  list: () => api.get('/vector-stores/'),
  get: (vectorStoreId) => api.get(`/vector-stores/${vectorStoreId}`),
  create: (data) => api.post('/vector-stores/', data),
  delete: (vectorStoreId) => api.delete(`/vector-stores/${vectorStoreId}`),
  // Removes the stores gone at OpenAI, and clears the cached lists.
  refresh: () => api.post('/vector-stores/refresh'),
  refreshStore: (vectorStoreId) => api.post(`/vector-stores/${vectorStoreId}/refresh`),

  getFiles: (vectorStoreId) => api.get(`/vector-stores/${vectorStoreId}/files`),
  uploadFile: (vectorStoreId, file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/vector-stores/${vectorStoreId}/files`, form, multipart);
  },
  removeFile: (vectorStoreId, fileId) =>
    api.delete(`/vector-stores/${vectorStoreId}/files/${fileId}`),

  // Assignments: to a whole session, or to one of its DD types.
  assignToSession: (vectorStoreId, sessionId, assignment) =>
    api.put(`/vector-stores/${vectorStoreId}/assign-session/${sessionId}`, assignment),
  removeFromSession: (vectorStoreId, sessionId, ddTypeCode = null) =>
    api.delete(`/vector-stores/${vectorStoreId}/assign-session/${sessionId}`, {
      params: ddTypeCode ? { dd_type_code: ddTypeCode } : {},
    }),
  getSessionAssignments: (sessionId) => api.get(`/vector-stores/session/${sessionId}/assignments`),
};
