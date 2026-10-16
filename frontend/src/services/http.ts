import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { env } from '@/config/env'

export interface ApiError {
  status: number
  code: string
  message: string
  fieldErrors?: Record<string, string>
  retryAfterSeconds?: number
}

// In-memory token management
let inMemoryAccessToken: string | null = null
let refreshHandler: (() => Promise<string | null>) | null = null
let logoutHandler: (() => void) | null = null

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken
}

export function configureAuthHandlers(handlers: {
  refresh: () => Promise<string | null>
  logout: () => void
}): void {
  refreshHandler = handlers.refresh
  logoutHandler = handlers.logout
}

export const http = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 15000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request Interceptor: Attach in-memory JWT
http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (inMemoryAccessToken && config.headers) {
    config.headers.Authorization = `Bearer ${inMemoryAccessToken}`
  }
  return config
})

// Refresh queue synchronization for single-flight refresh
let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else if (token) {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

// Friendly human-readable copy by HTTP status
export function getFriendlyStatusMessage(status?: number): string {
  switch (status) {
    case 400:
      return 'Please check the information entered.'
    case 401:
      return 'Session expired. Please log in again.'
    case 403:
      return 'You do not have permission to view or do this.'
    case 404:
      return 'The requested deal or information is no longer available.'
    case 409:
      return 'This action has already been performed.'
    case 410:
      return 'This code has expired. Please refresh your screen.'
    case 429:
      return 'Too many attempts. Please wait a few minutes before trying again.'
    case 500:
    case 502:
    case 503:
    case 504:
      return 'Our servers are experiencing heavy traffic. Please try again in a moment.'
    default:
      return 'Unable to connect. Please check your internet connection.'
  }
}

export function normalizeError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<any>
    const status = axiosErr.response?.status || 0
    const data = axiosErr.response?.data
    const fieldErrors: Record<string, string> = {}

    let message = getFriendlyStatusMessage(status)
    let code = 'ERROR'
    let retryAfterSeconds: number | undefined

    if (status === 429) {
      code = 'RATE_LIMIT_EXCEEDED'
      const retryHeader = axiosErr.response?.headers?.['retry-after']
      retryAfterSeconds = retryHeader ? parseInt(retryHeader, 10) : 60
      if (isNaN(retryAfterSeconds) || retryAfterSeconds <= 0) retryAfterSeconds = 60
      message = `Too many requests. Please wait ${retryAfterSeconds} seconds before retrying.`
    }

    // Backend ResponseEnvelope / ErrorEnvelope: error.code, error.message, error.details
    if (data?.error) {
      if (data.error.code) code = data.error.code
      if (data.error.message) message = data.error.message

      if (Array.isArray(data.error.details)) {
        data.error.details.forEach((item: any) => {
          if (item?.field && item?.message) {
            fieldErrors[item.field] = item.message
          } else if (item?.loc) {
            const fieldName = item.loc[item.loc.length - 1]
            fieldErrors[fieldName] = item.msg || item.message || 'Invalid value'
          }
        })
      } else if (data.error.details && typeof data.error.details === 'object') {
        Object.entries(data.error.details).forEach(([k, v]) => {
          fieldErrors[k] = String(v)
        })
      }
    } else if (status === 422 && Array.isArray(data?.detail)) {
      data.detail.forEach((item: any) => {
        const fieldName = item.loc ? item.loc[item.loc.length - 1] : 'field'
        fieldErrors[fieldName] = item.msg || 'Invalid value'
      })
      message = 'Please correct the highlighted fields.'
      code = 'VALIDATION_ERROR'
    } else if (typeof data?.detail === 'string') {
      message = data.detail
    } else if (data?.message) {
      message = data.message
    }

    return { status, code, message, fieldErrors, retryAfterSeconds }
  }

  if (error instanceof Error) {
    return { status: 0, code: 'CLIENT_ERROR', message: error.message }
  }

  return { status: 0, code: 'UNKNOWN_ERROR', message: 'An unexpected error occurred.' }
}

// Response Interceptor: 401 token refresh queue & envelope unwrapping
http.interceptors.response.use(
  (response) => {
    // Envelope unwrapping
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return response.data.data
    }
    return response.data
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // On 401: attempt single-flight token refresh
    if (error.response?.status === 401 && !originalRequest._retry && refreshHandler) {
      // Avoid looping on auth endpoints
      if (
        originalRequest.url?.includes('/auth/refresh') ||
        originalRequest.url?.includes('/auth/otp') ||
        originalRequest.url?.includes('/auth/staff-login') ||
        originalRequest.url?.includes('/auth/admin-login')
      ) {
        return Promise.reject(normalizeError(error))
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            return http(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const newToken = await refreshHandler()
        if (newToken) {
          setAccessToken(newToken)
          processQueue(null, newToken)
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
          }
          return http(originalRequest)
        } else {
          throw new Error('Refresh failed')
        }
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        if (logoutHandler) {
          logoutHandler()
        }
        return Promise.reject(normalizeError(error))
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(normalizeError(error))
  }
)
