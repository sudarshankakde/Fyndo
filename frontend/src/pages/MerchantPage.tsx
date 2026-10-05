import React, { useState } from 'react'
import { CheckCircle2, ShieldCheck, ArrowRight, UserCheck } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { setAuthModalOpen } from '@/store/slices/uiSlice'
import { logout, setAuthSession } from '@/store/slices/authSlice'
import { useTranslation } from '@/hooks/useTranslation'
import { Button } from '@/components/ui/Button'
import { MerchantSidebar, MerchantTab } from '@/components/merchant/dashboard/MerchantSidebar'
import { MerchantOverviewView } from '@/components/merchant/dashboard/MerchantOverviewView'
import { MerchantOffersView } from '@/components/merchant/dashboard/MerchantOffersView'
import { MerchantNewOfferView } from '@/components/merchant/dashboard/MerchantNewOfferView'
import { MerchantProfileView } from '@/components/merchant/dashboard/MerchantProfileView'
import { MerchantStaffView } from '@/components/merchant/dashboard/MerchantStaffView'
import { MerchantAnalyticsView } from '@/components/merchant/dashboard/MerchantAnalyticsView'
import { PermissionGate } from '@/components/common/PermissionGate'

export const MerchantPage: React.FC = () => {
  const { t } = useTranslation()
  const dispatch = useAppDispatch()
  const { isAuthenticated, user } = useAppSelector((state) => state.auth)

  const [activeTab, setActiveTab] = useState<MerchantTab>('overview')
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 5000)
  }

  // Quick 1-click Demo Merchant Login for instant testing
  const handleDemoLogin = () => {
    dispatch(
      setAuthSession({
        accessToken: 'demo_token_merchant_sitabuldi',
        refreshToken: 'demo_refresh_token',
        user: {
          id: 'usr_demo_01',
          phone: '+919876543210',
          full_name: 'Sudarshan (Haldirams Owner)',
          role: 'MERCHANT',
          preferred_language: 'en',
        },
      })
    )
    showToast('Logged in as Store Owner: Haldirams Sitabuldi')
  }

  return (
    <div className="min-h-screen py-8 sm:py-12 space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-3.5 rounded-lg border border-emerald-800/80 bg-emerald-950/80 text-emerald-300 text-xs font-mono flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-stone-400 hover:text-stone-200 text-xs font-mono ml-4"
          >
            [CLOSE]
          </button>
        </div>
      )}

      {/* Unauthenticated Demo Quick-Access Bar */}
      {!isAuthenticated && (
        <div className="surface-card p-4 rounded-xl border border-amber-800/60 bg-amber-950/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <UserCheck className="h-4 w-4 text-amber-400 shrink-0" />
            <p className="text-xs text-stone-200 font-medium">
              You are exploring the Store Manager portal. Log in to manage live store videos, coupons, and staff PINs.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button variant="primary" size="sm" onClick={handleDemoLogin} className="text-xs font-mono">
              1-Click Demo Login
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => dispatch(setAuthModalOpen(true))}
              className="text-xs"
            >
              Sign In with OTP
            </Button>
          </div>
        </div>
      )}

      {/* Dashboard Asymmetric Layout: Sidebar + Active Page */}
      <div className="flex flex-col lg:flex-row items-start gap-8">
        {/* Sidebar */}
        <MerchantSidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          user={user}
          onLogout={() => {
            dispatch(logout())
            showToast('Signed out of store manager.')
          }}
          onOpenLogin={() => dispatch(setAuthModalOpen(true))}
          storeName={user?.full_name ? "Haldiram's Sitabuldi" : "Local Retail Store"}
        />

        {/* Main Tab Content View */}
        <main className="flex-1 w-full min-w-0">
          {activeTab === 'overview' && (
            <MerchantOverviewView onNavigateTab={setActiveTab} />
          )}

          {activeTab === 'offers' && (
            <MerchantOffersView onPostNew={() => setActiveTab('new-offer')} />
          )}

          {activeTab === 'new-offer' && (
            <PermissionGate permission="CREATE_OFFER" showWarning>
              <MerchantNewOfferView
                onSuccess={(msg) => {
                  showToast(msg)
                  setActiveTab('offers')
                }}
              />
            </PermissionGate>
          )}

          {activeTab === 'profile' && (
            <PermissionGate permission="EDIT_STORE_PROFILE" showWarning>
              <MerchantProfileView onSuccess={showToast} />
            </PermissionGate>
          )}

          {activeTab === 'staff' && (
            <PermissionGate permission="MANAGE_STAFF_PINS" showWarning>
              <MerchantStaffView onSuccess={showToast} />
            </PermissionGate>
          )}

          {activeTab === 'analytics' && (
            <PermissionGate permission="VIEW_STORE_ANALYTICS" showWarning>
              <MerchantAnalyticsView />
            </PermissionGate>
          )}
        </main>
      </div>
    </div>
  )
}
