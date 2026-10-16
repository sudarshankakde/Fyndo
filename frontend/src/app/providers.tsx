import React, { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Provider } from 'react-redux'
import { store, useAppDispatch, useAppSelector } from '@/store'
import { authService } from '@/services/authService'
import { configureAuthHandlers, setAccessToken } from '@/services/http'
import { logout, setAuthSession, setStaffSession, setBootComplete } from '@/store/slices/authSlice'
import { applyGoogleTranslation } from '@/utils/googleTranslate'
import { DevToolsOverlay } from '@/dev/DevToolsOverlay'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { OfflineBanner } from '@/components/common/OfflineBanner'
import { env } from '@/config/env'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Do not retry 4xx errors or 429 rate-limited requests
        if (error?.status >= 400 && error?.status < 500) return false
        if (error?.status === 429) return false
        return failureCount < 2
      },
      staleTime: 30000,
      refetchOnWindowFocus: false,
    },
  },
})

const SessionBootstrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dispatch = useAppDispatch()
  const { status } = useAppSelector((state) => state.auth)
  const { language } = useAppSelector((state) => state.ui)

  // React to language switches across the entire application
  useEffect(() => {
    applyGoogleTranslation(language)
  }, [language])

  useEffect(() => {
    // Configure central axios interceptor handlers
    configureAuthHandlers({
      refresh: async () => {
        try {
          const res = await authService.refreshToken()
          return res.access_token
        } catch {
          return null
        }
      },
      logout: () => {
        dispatch(logout())
        queryClient.clear()
      },
    })

    // Cross-tab logout listener
    const authChannel =
      typeof window !== 'undefined' && 'BroadcastChannel' in window
        ? new BroadcastChannel('fyndo_auth')
        : null

    if (authChannel) {
      authChannel.onmessage = (event) => {
        if (event.data?.type === 'LOGOUT') {
          dispatch(logout())
          queryClient.clear()
        }
      }
    }

    // Session Boot Logic via httpOnly refresh cookie
    const bootSession = async () => {
      try {
        const tokens = await authService.refreshToken()
        setAccessToken(tokens.access_token)

        const profile = await authService.getMe()
        if (profile.role === 'ROLE_CASHIER') {
          dispatch(
            setStaffSession({
              accessToken: tokens.access_token,
              staffId: profile.id,
              staffName: profile.full_name || 'Counter Staff',
              merchantId: (profile as any).merchant_id || '',
              businessName: (profile as any).business_name || 'Store POS',
            })
          )
        } else {
          dispatch(
            setAuthSession({
              accessToken: tokens.access_token,
              user: profile,
            })
          )
        }
      } catch {
        dispatch(setBootComplete(false))
      }
    }

    bootSession()

    return () => {
      if (authChannel) {
        authChannel.close()
      }
    }
  }, [dispatch])

  if (status === 'booting') {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20 mb-4 animate-bounce">
          <span className="text-white text-xl font-bold tracking-tight">F</span>
        </div>
        <p className="text-sm font-semibold text-stone-600">Loading Fyndo...</p>
      </div>
    )
  }

  return (
    <>
      <OfflineBanner />
      {children}
      {env.enableDevTools && <DevToolsOverlay />}
    </>
  )
}

export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <SessionBootstrapper>{children}</SessionBootstrapper>
        </QueryClientProvider>
      </Provider>
    </ErrorBoundary>
  )
}
