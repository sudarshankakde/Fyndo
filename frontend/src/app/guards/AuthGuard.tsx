import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAppSelector } from '@/store'
import { UserRole } from '@/types/auth'

interface AuthGuardProps {
  children: React.ReactNode
  allowedRoles?: UserRole[]
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children, allowedRoles }) => {
  const location = useLocation()
  const { isAuthenticated, user, staff } = useAppSelector((state) => state.auth)

  // 1. Unauthenticated check - redirect to specific login per area
  if (!isAuthenticated) {
    if (location.pathname.startsWith('/pos')) {
      return <Navigate to="/pos/login" replace />
    }
    if (location.pathname.startsWith('/admin')) {
      return <Navigate to="/admin/login" replace />
    }
    const nextPath = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${nextPath}`} replace />
  }

  // 2. Staff POS check
  if (staff || user?.role === 'ROLE_CASHIER') {
    if (allowedRoles && !allowedRoles.includes('ROLE_CASHIER')) {
      return <Navigate to="/pos" replace />
    }
    return <>{children}</>
  }

  // 3. User role check
  if (user && allowedRoles && !allowedRoles.includes(user.role)) {
    // If a registered shopper tries to open Store Studio, redirect to onboarding KYC
    if (user.role === 'SHOPPER' && location.pathname.startsWith('/merchant')) {
      return <Navigate to="/merchant/onboarding" replace />
    }
    if (user.role === 'SUPER_ADMIN') {
      return <Navigate to="/admin" replace />
    }
    if (user.role === 'MERCHANT') {
      return <Navigate to="/merchant" replace />
    }
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
