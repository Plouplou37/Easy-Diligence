import axios from 'axios';
import { API_URL } from '../config/api.config.js';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Every request carries the access token, when there is one.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Requests whose 401 is an answer for the user ("wrong password"), not an
// expired session: they must not send anyone back to the login page.
const AUTH_FORMS = ['/auth/login', '/auth/register', '/auth/reset-password'];

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';
    if (status === 401 && !AUTH_FORMS.some((path) => url.startsWith(path))) {
      // The session has expired: start again from the login page.
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    } else if (status === 403) {
      // The resource exists but is not the user's.
      error.userMessage =
        error.response?.data?.detail || "You don't have permission to access this resource.";
    }
    return Promise.reject(error);
  }
);

/** The message to show for a failed request: the API's own, when it gave one. */
export const errorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ');
  return fallback || error?.message || 'Something went wrong';
};

const multipart = { headers: { 'Content-Type': 'multipart/form-data' } };

const authAPI = {
  // FastAPI's OAuth2 form: the e-mail goes in the "username" field.
  login: (email, password) =>
    api.post('/auth/login', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  me: () => api.get('/auth/me'),
  register: (data) => api.post('/auth/register', data),
  logout: () => api.post('/auth/logout'),
  updateProfile: (updates) => api.put('/auth/profile', updates),
  changePassword: (currentPassword, newPassword) =>
    api.put('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  requestPasswordReset: (email) => api.post('/auth/reset-password', { email }),
};

const companyAPI = {
  create: (data) => api.post('/company/', data),
  list: (params) => api.get('/company/', { params }),
  update: (id, data) => api.put(`/company/${id}`, data),
};

const sessionAPI = {
  create: (data) => api.post('/session/', data),
  get: (id) => api.get(`/session/${id}`),
  getStatus: (id) => api.get(`/session/${id}/status`),
  delete: (id) => api.delete(`/session/${id}`),
};

// Every session with the state of its DD types, in one call.
const dashboardAPI = {
  sessions: () => api.get('/dashboard/sessions'),
};

const processingAPI = {
  start: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/start`),
  resume: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/resume`),
  pause: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/pause`),
};

const answersAPI = {
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

const questionsAPI = {
  getDdTypes: (activeOnly = true) =>
    api.get('/questions/dd-types', { params: { active_only: activeOnly } }),
  createQuestion: (ddTypeCode, sectionId, question) =>
    api.post(`/questions/dd-types/${ddTypeCode}/sections/${sectionId}/questions`, question),
  updateQuestion: (questionId, question) => api.put(`/questions/questions/${questionId}`, question),
  deleteQuestion: (questionId) => api.delete(`/questions/questions/${questionId}`),
  reorderQuestion: (questionId, newOrder) =>
    api.patch(`/questions/questions/${questionId}/reorder`, { new_order: newOrder }),
  createSection: (ddTypeCode, section) =>
    api.post(`/questions/dd-types/${ddTypeCode}/sections`, section),
  updateSection: (sectionId, section) => api.put(`/questions/sections/${sectionId}`, section),
  deleteSection: (sectionId) => api.delete(`/questions/sections/${sectionId}`),
  reorderSection: (sectionId, newOrder) =>
    api.patch(`/questions/sections/${sectionId}/reorder`, { new_order: newOrder }),
};

const ddTypesAPI = {
  list: (activeOnly = true) => api.get('/dd-types/', { params: { active_only: activeOnly } }),
  create: (ddType) => api.post('/dd-types/', ddType),
  update: (ddTypeCode, ddType) => api.put(`/dd-types/${ddTypeCode}`, ddType),
  delete: (ddTypeCode) => api.delete(`/dd-types/${ddTypeCode}`),
  importFromFile: (formData) => api.post('/dd-types/import', formData, multipart),
  activate: (ddTypeCode) => api.post(`/dd-types/${ddTypeCode}/activate`),
  deactivate: (ddTypeCode) => api.post(`/dd-types/${ddTypeCode}/deactivate`),
  validate: (ddTypeCode) => api.put(`/dd-types/${ddTypeCode}/validate`),
};

const vectorStoresAPI = {
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

// Section summaries and the DD type synthesis.
const summariesAPI = {
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

const adminAPI = {
  getUsers: (params = {}) => api.get('/admin/users', { params }),
  updateUserRole: (userId, role) => api.put(`/admin/users/${userId}/role`, { role }),
  updateUserStatus: (userId, isActive) =>
    api.put(`/admin/users/${userId}/status`, { is_active: isActive }),
  deleteUser: (userId) => api.delete(`/admin/users/${userId}`),
};

export {
  adminAPI,
  answersAPI,
  authAPI,
  companyAPI,
  dashboardAPI,
  ddTypesAPI,
  processingAPI,
  questionsAPI,
  sessionAPI,
  summariesAPI,
  vectorStoresAPI,
};
export default api;
