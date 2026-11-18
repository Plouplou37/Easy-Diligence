import axios from 'axios';
import { API_URL } from '../config/api.config.js';

// Create API instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    } else if (error.response?.status === 403) {
      // Forbidden: the resource exists but isn't owned by this user.
      // Surface a clear message; callers may still handle the rejection.
      const detail = error.response?.data?.detail;
      error.userMessage = detail || "You don't have permission to access this resource.";
    }
    return Promise.reject(error);
  }
);

// Company API
const companyAPI = {
    create: (data) => api.post('/company', data),
    list: (params) => api.get('/company', { params }),
    get: (id) => api.get(`/company/${id}`),
    update: (id, data) => api.put(`/company/${id}`, data),
  };

// Session API
const sessionAPI = {
    create: (data) => api.post('/session', data),
    get: (id) => api.get(`/session/${id}`),
    getStatus: (id) => api.get(`/session/${id}/status`),
    list: (params) => api.get('/session', { params }),
    delete: (id) => api.delete(`/session/${id}`),
  };

// Dashboard API: every session with the state of its DD types, in one call
const dashboardAPI = {
    sessions: () => api.get('/dashboard/sessions'),
  };

// Documents API
const documentsAPI = {
    uploadToVectorStore: (sessionId, vectorStoreId, files) => {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append('files', file);
      });
      return api.post(`/documents/session/${sessionId}/upload/${vectorStoreId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },
    list: (sessionId) => api.get(`/documents/session/${sessionId}`),
    delete: (documentId) => api.delete(`/documents/${documentId}`)
  };

// Processing API
const processingAPI = {
    start: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/start`),
    resume: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/resume`),
    getProgress: (sessionId, ddType) => api.get(`/processing/session/${sessionId}/dd/${ddType}/progress`),
    pause: (sessionId, ddType) => api.post(`/processing/session/${sessionId}/dd/${ddType}/pause`),
  };

// Answers API
const answersAPI = {
    getAll: (params = {}) => api.get('/answers/all', { params }),
    getStats: () => api.get('/answers/stats'),
    getBySession: (sessionId, params) => api.get(`/answers/session/${sessionId}`, { params }),
    getByExecution: (executionId) => api.get(`/answers/by-execution/${executionId}`),

    // Get single answer
    get: (answerId) => api.get(`/answers/${answerId}`),

    // Update answer
    update: (answerId, data) => api.put(`/answers/${answerId}`, data),

    // Update answer status
    updateStatus: (answerId, status) => api.patch(`/answers/${answerId}/status`, { status }),

    // Get answer with complete history
    getWithHistory: (answerId) => api.get(`/answers/${answerId}/with-history`),

    // Get answer history
    getHistory: (answerId) => api.get(`/answers/${answerId}/history`),

    // Create new version of answer
    createVersion: (answerId, versionData) => api.post(`/answers/${answerId}/versions`, versionData),

    // Revert to previous version
    revertToVersion: (answerId, version) => api.post(`/answers/${answerId}/revert`, { version }),

    // Regenerate an answer via the AI (creates a new version, status needs_review).
    // Optional guidance: instruction (re-prompt), referenceUrl (consulted via
    // web_search), file (added to the session vector store + answer sources).
    regenerate: (answerId, { instruction, referenceUrl, file } = {}) => {
      const fd = new FormData();
      if (instruction)  fd.append('instruction', instruction);
      if (referenceUrl) fd.append('reference_url', referenceUrl);
      if (file)         fd.append('file', file);
      return api.post(`/answers/${answerId}/regenerate`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },

    // Get specific version
    getVersion: (answerId, version) => api.get(`/answers/${answerId}/versions/${version}`),

    // Get original AI-generated answer
    getOriginal: (answerId) => api.get(`/answers/${answerId}/original`),

    // Export answers
    export: (sessionId, format) => api.get(`/answers/session/${sessionId}/export`, {
      params: { format },
      responseType: 'blob',
    }),
  };

// Questions API
const questionsAPI = {
    getDdTypes: (activeOnly = true) =>
      api.get('/questions/dd-types', { params: { active_only: activeOnly } }),
    listSectionQuestions: (ddTypeCode, sectionId) =>
      api.get(`/questions/dd-types/${ddTypeCode}/sections/${sectionId}/questions`),
    createQuestion: (ddTypeCode, sectionId, question) => api.post(`/questions/dd-types/${ddTypeCode}/sections/${sectionId}/questions`, question),
    updateQuestion: (questionId, question) => api.put(`/questions/questions/${questionId}`, question),
    deleteQuestion: (questionId) => api.delete(`/questions/questions/${questionId}`),
    reorderQuestion: (questionId, newOrder) => api.patch(`/questions/questions/${questionId}/reorder`, { new_order: newOrder }),
    createSection: (ddTypeCode, section) => api.post(`/questions/dd-types/${ddTypeCode}/sections`, section),
    updateSection: (sectionId, section) => api.put(`/questions/sections/${sectionId}`, section),
    deleteSection: (sectionId) => api.delete(`/questions/sections/${sectionId}`),
    reorderSection: (sectionId, newOrder) => api.patch(`/questions/sections/${sectionId}/reorder`, { new_order: newOrder })
  };

// DD Types API
const ddTypesAPI = {
    list: (activeOnly = true) => api.get('/dd-types/', { params: { active_only: activeOnly } }),
    get: (ddTypeCode) => api.get(`/dd-types/${ddTypeCode}`),
    create: (ddType) => api.post('/dd-types/', ddType),
    update: (ddTypeCode, ddType) => api.put(`/dd-types/${ddTypeCode}`, ddType),
    delete: (ddTypeCode) => api.delete(`/dd-types/${ddTypeCode}`),
    importFromFile: (formData) => api.post('/dd-types/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    activate: (ddTypeCode) => api.post(`/dd-types/${ddTypeCode}/activate`),
    deactivate: (ddTypeCode) => api.post(`/dd-types/${ddTypeCode}/deactivate`),
    validate: (ddTypeCode) => api.put(`/dd-types/${ddTypeCode}/validate`)
  };

// Vector Store API
const vectorStoresAPI = {
    list: () => api.get('/vector-stores/'),
    get: (vectorStoreId) => api.get(`/vector-stores/${vectorStoreId}`),
    create: (vectorStoreData) => api.post('/vector-stores/', vectorStoreData),
    update: (vectorStoreId, updateData) => api.patch(`/vector-stores/${vectorStoreId}`, updateData),
    delete: (vectorStoreId) => api.delete(`/vector-stores/${vectorStoreId}`),
    refresh: () => api.post('/vector-stores/refresh'),
    refreshStore: (vectorStoreId) => api.post(`/vector-stores/${vectorStoreId}/refresh`),

    // File management
    getFiles: (vectorStoreId) => api.get(`/vector-stores/${vectorStoreId}/files`),
    uploadFile: (vectorStoreId, file) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post(`/vector-stores/${vectorStoreId}/files`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
    removeFile: (vectorStoreId, fileId) => api.delete(`/vector-stores/${vectorStoreId}/files/${fileId}`),
    
    // Enhanced features
    search: (vectorStoreId, searchRequest) => 
      api.post(`/vector-stores/${vectorStoreId}/search`, searchRequest),
    getFileContent: (vectorStoreId, fileId) => 
      api.get(`/vector-stores/${vectorStoreId}/files/${fileId}/content`),
    getOriginalFile: (vectorStoreId, fileId) => 
      api.get(`/vector-stores/${vectorStoreId}/files/${fileId}/original`, { responseType: 'blob' }),
    
    // File batch operations
    createFileBatch: (vectorStoreId, batchRequest) => 
      api.post(`/vector-stores/${vectorStoreId}/file_batches`, batchRequest),
    getFileBatch: (vectorStoreId, batchId) => 
      api.get(`/vector-stores/${vectorStoreId}/file_batches/${batchId}`),
    cancelFileBatch: (vectorStoreId, batchId) => 
      api.post(`/vector-stores/${vectorStoreId}/file_batches/${batchId}/cancel`),
    listBatchFiles: (vectorStoreId, batchId, params = {}) => 
      api.get(`/vector-stores/${vectorStoreId}/file_batches/${batchId}/files`, { params }),
    
    // File attributes and metadata
    updateFileAttributes: (vectorStoreId, fileId, attributes) => 
      api.post(`/vector-stores/${vectorStoreId}/files/${fileId}/attributes`, { attributes }),
    getFileAttributes: (vectorStoreId, fileId) => 
      api.get(`/vector-stores/${vectorStoreId}/files/${fileId}/attributes`),
    
    // Session assignments
    assignToSession: (vectorStoreId, sessionId, assignment) => 
      api.put(`/vector-stores/${vectorStoreId}/assign-session/${sessionId}`, assignment),
    removeFromSession: (vectorStoreId, sessionId, ddTypeCode = null) => 
      api.delete(`/vector-stores/${vectorStoreId}/assign-session/${sessionId}`, { 
        params: ddTypeCode ? { dd_type_code: ddTypeCode } : {} 
      }),
    getSessionAssignments: (sessionId) => 
      api.get(`/vector-stores/session/${sessionId}/assignments`)
  };

// Summaries API (section summaries + per-DD-type synthesis)
const summariesAPI = {
    // Generate (and persist) section summaries + the DD-type synthesis
    generate: (sessionId, ddType) => api.post(`/summaries/session/${sessionId}/dd/${ddType}/generate`),
    // Same thing through the OpenAI Batch API: half price, but the job runs
    // outside the request (up to 24h). Returns immediately; poll batchStatus.
    generateBatch: (sessionId, ddType) =>
      api.post(`/summaries/session/${sessionId}/dd/${ddType}/generate/batch`),
    // Poll a batch. Collecting the results happens server-side on this call, so
    // it is also what turns a completed batch into stored summaries.
    batchStatus: (sessionId, ddType) =>
      api.get(`/summaries/session/${sessionId}/dd/${ddType}/batch`),
    // Stop a batch still in OpenAI's queue. Requests already completed stay
    // billed; the backend checks the real state first and leaves a batch that
    // has meanwhile finished alone.
    cancelBatch: (sessionId, ddType) =>
      api.post(`/summaries/session/${sessionId}/dd/${ddType}/batch/cancel`),
    // List stored summaries for a session (optionally filtered by DD type code)
    list: (sessionId, ddType = null) => api.get(`/summaries/session/${sessionId}`, {
      params: ddType ? { dd_type: ddType } : {},
    }),
    // Edit a summary's text before export
    update: (summaryId, summaryText) => api.put(`/summaries/${summaryId}`, { summary_text: summaryText }),
  };

// Admin API
const adminAPI = {
    getUsers: (params = {}) => api.get('/admin/users', { params }),
    updateUserRole: (userId, role) => api.patch(`/admin/users/${userId}/role`, { role }),
    updateUserStatus: (userId, isActive) => api.patch(`/admin/users/${userId}/status`, { is_active: isActive }),
    deleteUser: (userId) => api.delete(`/admin/users/${userId}`)
  };

// Executions API
const executionsAPI = {
    // Get execution summary for answer management
    getSummary: (params = {}) => api.get('/executions/summary', { params }),
    
    // Get execution details
    get: (executionId) => api.get(`/executions/${executionId}`),
    
    // List executions for a session
    listBySession: (sessionId, params = {}) => api.get(`/executions/session/${sessionId}`, { params }),
    
    // Create new execution
    create: (sessionId, ddTypeId) => api.post('/executions/', { session_id: sessionId, dd_type_id: ddTypeId }),
    
    // Update execution status
    updateStatus: (executionId, status, data = {}) => api.put(`/executions/${executionId}/status`, { status, ...data }),
    
    // Start execution
    start: (executionId) => api.post(`/executions/${executionId}/start`),
    
    // Validate execution
    validate: (executionId, validationData) => api.post(`/executions/${executionId}/validate`, validationData),
    
    // Get execution responses
    getResponses: (executionId) => api.get(`/executions/${executionId}/responses`),
    
    // Get execution messages
    getMessages: (executionId) => api.get(`/executions/${executionId}/messages`)
  };


export { companyAPI, sessionAPI, dashboardAPI, documentsAPI, processingAPI, answersAPI, questionsAPI, ddTypesAPI, vectorStoresAPI, adminAPI, executionsAPI, summariesAPI };
export default api;