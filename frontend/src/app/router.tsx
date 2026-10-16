import React, { Suspense, lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { ShopperLayout } from './layouts/ShopperLayout'
import { MerchantLayout } from './layouts/MerchantLayout'
import { PosLayout } from './layouts/PosLayout'
import { AdminLayout } from './layouts/AdminLayout'
import { AuthGuard } from './guards/AuthGuard'

// Lazy-loaded routes per role bundle for optimal mobile bundle splitting
const LoginPage = lazy(() => import('@/pages/LoginPage').then(m => ({ default: m.LoginPage })))
const PosLoginPage = lazy(() => import('@/pages/PosLoginPage').then(m => ({ default: m.PosLoginPage })))
const AdminLoginPage = lazy(() => import('@/pages/AdminLoginPage').then(m => ({ default: m.AdminLoginPage })))
const FeedPage = lazy(() => import('@/pages/FeedPage').then(m => ({ default: m.FeedPage })))
const WalletPage = lazy(() => import('@/pages/WalletPage').then(m => ({ default: m.WalletPage })))
const ProfilePage = lazy(() => import('@/pages/ProfilePage').then(m => ({ default: m.ProfilePage })))
const MerchantPage = lazy(() => import('@/pages/MerchantPage').then(m => ({ default: m.MerchantPage })))
const MerchantOnboardingPage = lazy(() => import('@/pages/MerchantOnboardingPage').then(m => ({ default: m.MerchantOnboardingPage })))
const MerchantOfferWizardPage = lazy(() => import('@/pages/MerchantOfferWizardPage').then(m => ({ default: m.MerchantOfferWizardPage })))
const StorefrontPage = lazy(() => import('@/pages/StorefrontPage').then(m => ({ default: m.StorefrontPage })))
const ReelDetailPage = lazy(() => import('@/pages/ReelDetailPage').then(m => ({ default: m.ReelDetailPage })))
const PosPage = lazy(() => import('@/pages/PosPage').then(m => ({ default: m.PosPage })))
const AdminPage = lazy(() => import('@/pages/AdminPage').then(m => ({ default: m.AdminPage })))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })))

const SuspenseWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Suspense
    fallback={
      <div className="flex-1 flex items-center justify-center p-8 text-stone-400 text-xs font-semibold">
        <span className="w-2 h-2 rounded-full bg-primary animate-ping mr-2" />
        Loading...
      </div>
    }
  >
    {children}
  </Suspense>
)

export const router = createBrowserRouter([
  // Public Auth
  {
    path: '/login',
    element: (
      <SuspenseWrapper>
        <LoginPage />
      </SuspenseWrapper>
    ),
  },
  {
    path: '/pos/login',
    element: (
      <SuspenseWrapper>
        <PosLoginPage />
      </SuspenseWrapper>
    ),
  },
  {
    path: '/admin/login',
    element: (
      <SuspenseWrapper>
        <AdminLoginPage />
      </SuspenseWrapper>
    ),
  },

  // Shopper Layout (Desktop responsive frame)
  {
    path: '/',
    element: <ShopperLayout />,
    children: [
      {
        index: true,
        element: (
          <SuspenseWrapper>
            <FeedPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: 'wallet',
        element: (
          <SuspenseWrapper>
            <WalletPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: 'store/:id',
        element: (
          <SuspenseWrapper>
            <StorefrontPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: 'reel/:id',
        element: (
          <SuspenseWrapper>
            <ReelDetailPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: 'profile',
        element: (
          <AuthGuard allowedRoles={['SHOPPER', 'MERCHANT', 'SUPER_ADMIN']}>
            <SuspenseWrapper>
              <ProfilePage />
            </SuspenseWrapper>
          </AuthGuard>
        ),
      },
    ],
  },

  // Merchant Onboarding
  {
    path: '/merchant/onboarding',
    element: (
      <AuthGuard allowedRoles={['SHOPPER', 'MERCHANT']}>
        <SuspenseWrapper>
          <MerchantOnboardingPage />
        </SuspenseWrapper>
      </AuthGuard>
    ),
  },

  // Merchant Studio Hub
  {
    path: '/merchant',
    element: (
      <AuthGuard allowedRoles={['MERCHANT']}>
        <MerchantLayout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: (
          <SuspenseWrapper>
            <MerchantPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: 'offers/new',
        element: (
          <SuspenseWrapper>
            <MerchantOfferWizardPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: '*',
        element: (
          <SuspenseWrapper>
            <NotFoundPage area="merchant" />
          </SuspenseWrapper>
        ),
      },
    ],
  },

  // Cashier POS Scanner
  {
    path: '/pos',
    element: (
      <AuthGuard allowedRoles={['ROLE_CASHIER']}>
        <PosLayout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: (
          <SuspenseWrapper>
            <PosPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: '*',
        element: (
          <SuspenseWrapper>
            <NotFoundPage area="pos" />
          </SuspenseWrapper>
        ),
      },
    ],
  },

  // Super Admin Moderation
  {
    path: '/admin',
    element: (
      <AuthGuard allowedRoles={['SUPER_ADMIN']}>
        <AdminLayout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: (
          <SuspenseWrapper>
            <AdminPage />
          </SuspenseWrapper>
        ),
      },
      {
        path: '*',
        element: (
          <SuspenseWrapper>
            <NotFoundPage area="admin" />
          </SuspenseWrapper>
        ),
      },
    ],
  },

  // Catch-all
  {
    path: '*',
    element: (
      <SuspenseWrapper>
        <NotFoundPage />
      </SuspenseWrapper>
    ),
  },
])
