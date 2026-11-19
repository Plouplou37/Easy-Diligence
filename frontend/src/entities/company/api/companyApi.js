import { api } from '@/shared/api';

export const companyAPI = {
  create: data => api.post('/company/', data),
  list: params => api.get('/company/', { params }),
  update: (id, data) => api.put(`/company/${id}`, data),
};
