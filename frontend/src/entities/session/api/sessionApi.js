import { api } from '@/shared/api';

export const sessionAPI = {
  create: data => api.post('/session/', data),
  get: id => api.get(`/session/${id}`),
  getStatus: id => api.get(`/session/${id}/status`),
  delete: id => api.delete(`/session/${id}`),
};

// Every session with the state of its DD types, in one call.
export const dashboardAPI = {
  sessions: () => api.get('/dashboard/sessions'),
};
