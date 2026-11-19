import axios from 'axios';

// The API is called on the frontend's own origin, at /api: the Vite proxy
// forwards it in development (vite.config.js), nginx in Docker.
export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

/** Fired when the session has expired (a 401): the viewer logs out. */
export const SESSION_EXPIRED = 'session-expired';

// Every request carries the access token, when there is one.
api.interceptors.request.use(config => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Requests whose 401 is an answer for the user ("wrong password"), not an
// expired session.
const AUTH_FORMS = ['/auth/login', '/auth/register', '/auth/reset-password'];

api.interceptors.response.use(
  response => response,
  error => {
    const status = error.response?.status;
    const url = error.config?.url || '';
    if (status === 401 && !AUTH_FORMS.some(path => url.startsWith(path))) {
      window.dispatchEvent(new Event(SESSION_EXPIRED));
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
  if (Array.isArray(detail)) return detail.map(item => item.msg).join(', ');
  return fallback || error?.message || 'Something went wrong';
};

export const multipart = { headers: { 'Content-Type': 'multipart/form-data' } };
