import React, { useState } from 'react'
import { Wallet, Sparkles, LogIn, RefreshCw } from 'lucide-react'
import { useWallet } from '@/hooks/useWallet'
import { WalletCouponCard } from '@/components/coupon/WalletCouponCard'
import { Button } from '@/components/ui/Button'
import { useAppDispatch, useAppSelector } from '@/store'
import { setAuthModalOpen } from '@/store/slices/uiSlice'
import { useTranslation } from '@/hooks/useTranslation'
import { Link } from 'react-router-dom'

export const WalletPage: React.FC = () => {
  const { t } = useTranslation()
  const dispatch = useAppDispatch()
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated)
  const { coupons, isLoading, refetchWallet } = useWallet()

  const [activeTab, setActiveTab] = useState<'ALL' | 'ACTIVE' | 'REDEEMED'>('ACTIVE')

  if (!isAuthenticated) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6 max-w-sm mx-auto space-y-4">
        <div className="h-14 w-14 rounded-lg bg-stone-800 border border-stone-700 text-amber-400 flex items-center justify-center">
          <Wallet className="h-7 w-7" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-stone-100 mb-1.5 font-display">
            Your Digital Coupon Wallet
          </h2>
          <p className="text-xs text-stone-400 leading-relaxed font-sans">
            Log in with your mobile number to access your saved discount vouchers and show rotating security codes in stores.
          </p>
        </div>
        <Button
          variant="primary"
          size="lg"
          className="w-full"
          onClick={() => dispatch(setAuthModalOpen(true))}
        >
          <LogIn className="h-4 w-4 mr-2" />
          <span>{t.login}</span>
        </Button>
      </div>
    )
  }

  const filteredCoupons = coupons.filter((c) => {
    if (activeTab === 'ACTIVE') return c.status === 'CLAIMED' && !c.is_expired
    if (activeTab === 'REDEEMED') return c.status === 'REDEEMED'
    return true
  })

  return (
    <div className="min-h-screen pb-24 pt-8 max-w-lg mx-auto px-4">
      {/* Page Header */}
      <div className="flex items-center justify-between gap-2 mb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-stone-100 font-display">{t.wallet}</h1>
          <p className="text-xs text-stone-400 font-mono mt-0.5">In-store vouchers ready for cashier scan</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetchWallet()}
          className="text-stone-400 hover:text-white text-xs font-mono"
        >
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex rounded-lg bg-stone-900 border border-stone-800 p-1 mb-5 font-mono">
        {(['ACTIVE', 'REDEEMED', 'ALL'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
              activeTab === tab
                ? 'bg-stone-800 text-amber-400 border border-stone-700 font-bold'
                : 'text-stone-400 hover:text-stone-200'
            }`}
          >
            {tab === 'ACTIVE' ? 'Active' : tab === 'REDEEMED' ? 'Redeemed' : 'All Coupons'}
          </button>
        ))}
      </div>

      {/* Coupons List */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-7 w-7 text-amber-400 animate-spin" />
          <p className="text-xs text-stone-400 font-mono">Loading your coupons...</p>
        </div>
      ) : filteredCoupons.length > 0 ? (
        <div className="space-y-4">
          {filteredCoupons.map((coupon) => (
            <WalletCouponCard key={coupon.id} coupon={coupon} />
          ))}
        </div>
      ) : (
        <div className="surface-card py-16 text-center rounded-xl border border-stone-800 bg-stone-900/60 p-8 space-y-4">
          <div className="h-12 w-12 rounded bg-stone-800 text-stone-400 flex items-center justify-center mx-auto">
            <Wallet className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-stone-100 mb-1 font-display">
              {activeTab === 'ACTIVE' ? 'No active coupons right now' : 'No coupons found'}
            </h3>
            <p className="text-xs text-stone-400 leading-relaxed max-w-xs mx-auto font-sans">
              Explore nearby short reels in Nagpur and Mumbai to save exciting in-store deals!
            </p>
          </div>
          <Link to="/">
            <Button variant="primary" size="md">
              <Sparkles className="h-4 w-4 mr-2" />
              <span>Explore Deals Feed</span>
            </Button>
          </Link>
        </div>
      )}
    </div>
  )
}
