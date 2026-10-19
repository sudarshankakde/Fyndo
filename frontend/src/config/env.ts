/**
 * Environment configuration and validation.
 */
export const env = {
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  enableDevTools: import.meta.env.DEV && import.meta.env.VITE_DEV_TOOLS === 'true',
  mediaHosts: (import.meta.env.VITE_MEDIA_HOSTS || 'res.cloudinary.com').split(','),
}
