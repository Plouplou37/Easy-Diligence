import { api } from '@/shared/api';

export const authAPI = {
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
