import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { useAppSelector } from '@/store'
import { LoginPage } from '@/pages/LoginPage'
import { MerchantPage } from '@/pages/MerchantPage'
import { PosPage } from '@/pages/PosPage'
import { AdminPage } from '@/pages/AdminPage'
import { AuthenticatedHeader } from '@/components/common/AuthenticatedHeader'
import { DynamicQrModal } from '@/components/coupon/DynamicQrModal'

export const App: React.FC = () => {
  const { isAuthenticated, user, staff } = useAppSelector((state) => state.auth)

  return (
    <BrowserRouter>
      {/* Unauthenticated: Start directly at the dedicated Login Screen */}
      {!isAuthenticated ? (
        <LoginPage />
      ) : (
        <div className="min-h-screen bg-stone-950 text-stone-100 flex flex-col font-sans selection:bg-amber-500 selection:text-stone-950">
          <AuthenticatedHeader
            currentPortalName={
              staff || user?.role === 'ROLE_CASHIER'
                ? 'COUNTER SCANNER'
                : user?.role === 'SUPER_ADMIN'
                ? 'ADMIN DESK'
                : 'STORE MANAGER'
            }
          />

          <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {staff || user?.role === 'ROLE_CASHIER' ? (
              <PosPage />
            ) : user?.role === 'SUPER_ADMIN' ? (
              <AdminPage />
            ) : (
              <MerchantPage />
            )}
          </main>

          {/* Dynamic Security Code Modal for in-store coupon redemption */}
          <DynamicQrModal />
        </div>
      )}
    </BrowserRouter>
  )
}

export default App

