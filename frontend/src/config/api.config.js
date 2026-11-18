// The API is called on the frontend's own origin, at /api: the Vite proxy
// forwards it in development (vite.config.js), nginx in Docker.
export const API_URL = '/api';
