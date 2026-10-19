import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Ticket, RefreshCw, Compass, CheckCircle2, Clock, Sparkles, XCircle } from 'lucide-react'
import { useWallet } from '@/hooks/useWallet'
import { WalletCouponCard } from '@/components/coupon/WalletCouponCard'
import { ShopperRedemptionHistoryList } from '@/components/coupon/ShopperRedemptionHistoryList'
import { Button } from '@/components/ui/Button'
import { useAppSelector } from '@/store'

export const WalletPage: React.FC = () => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAppSelector((state) => state.auth)
  const { coupons, isLoading, refetchWallet } = useWallet()
  const [activeTab, setActiveTab] = useState<'ACTIVE' | 'REDEEMED' | 'EXPIRED' | 'ALL'>('ACTIVE')

  if (!isAuthenticated) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="max-w-md mx-auto bg-white rounded-3xl border border-stone-200/80 p-8 shadow-card text-center space-y-5 font-sans">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto shadow-inner">
            <Ticket className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-2xl font-black text-stone-900 tracking-tight">Your Savings Wallet</h2>
            <p className="text-sm text-stone-500 mt-2 leading-relaxed">
              Log in to manage your saved discount vouchers and present live checkout codes at local stores.
            </p>
          </div>
          <Button onClick={() => navigate('/login?next=/wallet')} variant="primary" size="lg" className="w-full">
            Log in with Mobile
          </Button>
          <div className="pt-2">
            <button
              onClick={() => navigate('/')}
              className="text-xs font-semibold text-stone-500 hover:text-stone-900 transition-colors"
            >
              Continue browsing nearby offers &rarr;
            </button>
          </div>
        </div>
      </div>
    )
  }

  const activeCount = coupons.filter((c) => c.status === 'CLAIMED' && !c.is_expired).length
  const redeemedCount = coupons.filter((c) => c.status === 'REDEEMED').length
  const expiredCount = coupons.filter((c) => c.is_expired || c.status === 'EXPIRED').length

  const filteredCoupons = coupons.filter((c) => {
    if (activeTab === 'ACTIVE') return c.status === 'CLAIMED' && !c.is_expired
    if (activeTab === 'REDEEMED') return c.status === 'REDEEMED'
    if (activeTab === 'EXPIRED') return c.is_expired || c.status === 'EXPIRED'
    return true
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 font-sans text-stone-900">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-stone-200/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-primary/10 text-primary">
              <Sparkles className="w-3 h-3" />
              Verified Savings
            </span>
          </div>
          <h1 className="text-3xl font-black tracking-tight text-stone-900">My Savings Wallet</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            Present dynamic QR vouchers at partner counters to unlock your exclusive discounts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => refetchWallet()} className="gap-2 text-xs font-bold">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-primary' : ''}`} />
            <span>Sync Wallet</span>
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate('/')} className="gap-2 text-xs font-bold">
            <Compass className="w-3.5 h-3.5" />
            <span>Find More Deals</span>
          </Button>
        </div>
      </div>

      {/* KPI Stats Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Ready to Use</p>
            <p className="text-3xl font-black text-stone-900 mt-1">{activeCount}</p>
            <p className="text-xs text-emerald-600 font-semibold mt-1">Active vouchers available</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Ticket className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Total Redeemed</p>
            <p className="text-3xl font-black text-stone-900 mt-1">{redeemedCount}</p>
            <p className="text-xs text-stone-500 font-semibold mt-1">Discounts claimed in-store</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Expired</p>
            <p className="text-3xl font-black text-stone-900 mt-1">{expiredCount}</p>
            <p className="text-xs text-amber-600 font-semibold mt-1">Passed validity cap</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-stone-200">
        <div className="flex items-center gap-1 sm:gap-4">
          <button
            onClick={() => setActiveTab('ACTIVE')}
            className={`pb-3 px-2 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'ACTIVE'
                ? 'border-primary text-primary'
                : 'border-transparent text-stone-500 hover:text-stone-900'
            }`}
          >
            <span>Active Vouchers</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-stone-100 text-stone-600">
              {activeCount}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('REDEEMED')}
            className={`pb-3 px-2 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'REDEEMED'
                ? 'border-primary text-primary'
                : 'border-transparent text-stone-500 hover:text-stone-900'
            }`}
          >
            <span>Past Redeemed</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-stone-100 text-stone-600">
              {redeemedCount}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('EXPIRED')}
            className={`pb-3 px-2 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'EXPIRED'
                ? 'border-primary text-primary'
                : 'border-transparent text-stone-500 hover:text-stone-900'
            }`}
          >
            <span>Expired Passes</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-stone-100 text-stone-600">
              {expiredCount}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('ALL')}
            className={`pb-3 px-2 text-sm font-bold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'ALL'
                ? 'border-primary text-primary'
                : 'border-transparent text-stone-500 hover:text-stone-900'
            }`}
          >
            <span>All History</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-stone-100 text-stone-600">
              {coupons.length}
            </span>
          </button>
        </div>
      </div>

      {/* Render Redeemed Receipts Ledger if in REDEEMED tab */}
      {activeTab === 'REDEEMED' && (
        <div className="pb-4">
          <ShopperRedemptionHistoryList />
        </div>
      )}

      {/* Coupons Desktop Grid */}
      {isLoading ? (
        <div className="py-20 text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
          <p className="text-sm text-stone-500 font-medium">Fetching your verified savings...</p>
        </div>
      ) : filteredCoupons.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCoupons.map((coupon) => (
            <WalletCouponCard key={coupon.id} coupon={coupon} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-3xl border border-stone-200/80 p-12 text-center shadow-card space-y-4 max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-stone-100 text-stone-400 flex items-center justify-center mx-auto">
            {activeTab === 'EXPIRED' ? <XCircle className="w-8 h-8" /> : <Ticket className="w-8 h-8" />}
          </div>
          <div>
            <h3 className="text-lg font-black text-stone-900">No {activeTab.toLowerCase()} vouchers found</h3>
            <p className="text-sm text-stone-500 max-w-sm mx-auto mt-1 leading-relaxed">
              Explore short video deals from local stores near you to save up to 50% on your everyday shopping.
            </p>
          </div>
          <Button onClick={() => navigate('/')} variant="primary" size="md" className="gap-2">
            <Compass className="w-4 h-4" />
            <span>Discover Nearby Deals</span>
          </Button>
        </div>
      )}
    </div>
  )
}
