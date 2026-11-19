import { api } from '@/shared/api';

// Account management, for admins.
export const adminAPI = {
  getUsers: (params = {}) => api.get('/admin/users', { params }),
  updateUserRole: (userId, role) => api.put(`/admin/users/${userId}/role`, { role }),
  updateUserStatus: (userId, isActive) =>
    api.put(`/admin/users/${userId}/status`, { is_active: isActive }),
  deleteUser: userId => api.delete(`/admin/users/${userId}`),
};
