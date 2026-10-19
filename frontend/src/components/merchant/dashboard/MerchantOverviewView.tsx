import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { PlusCircle, KeyRound, Store, TrendingUp, Users, Tag, ShieldCheck, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { merchantService } from '@/services/merchantService'
import { redemptionService } from '@/services/redemptionService'
import { MerchantTab } from '@/components/merchant/dashboard/MerchantSidebar'
import { formatRupees } from '@/utils/format'

interface MerchantOverviewViewProps {
  onNavigateTab: (tab: MerchantTab) => void
}

export const MerchantOverviewView: React.FC<MerchantOverviewViewProps> = ({ onNavigateTab }) => {
  const { data: profile } = useQuery({
    queryKey: ['merchant-profile'],
    queryFn: () => merchantService.getProfile(),
  })

  const { data: reels = [] } = useQuery({
    queryKey: ['merchant-reels'],
    queryFn: () => merchantService.listMyReels(),
  })

  const { data: analytics } = useQuery({
    queryKey: ['merchant-analytics', 'OVERVIEW'],
    queryFn: () => redemptionService.getMerchantAnalytics(),
  })

  const isApproved = profile?.kyc_status === 'APPROVED'
  const isPending = profile?.kyc_status === 'PENDING'
  const isRejected = profile?.kyc_status === 'REJECTED'

  const totalViews = reels.reduce((acc, r) => acc + (r.views_count || 0), 0)
  const activeOffers = reels.filter((r) => r.status === 'APPROVED').length

  return (
    <div className="space-y-6 font-sans text-stone-900">
      {/* Top Welcome Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-stone-200">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">
              {profile?.business_name || 'Store'} Overview
            </h2>
            {isApproved && <Badge variant="success">Verified Store</Badge>}
            {isPending && <Badge variant="amber">Pending Review</Badge>}
            {isRejected && <Badge variant="destructive">Action Required</Badge>}
          </div>
          <p className="text-xs text-stone-500 mt-0.5">
            Real-time counter redemptions and store offer performance.
          </p>
        </div>

        <Button
          variant="primary"
          size="sm"
          disabled={!isApproved}
          onClick={() => onNavigateTab('new-offer')}
          className="text-xs font-bold gap-1.5"
        >
          <PlusCircle className="h-4 w-4" />
          <span>Post New Offer</span>
        </Button>
      </div>

      {/* KYC Alert if not approved */}
      {isPending && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-start gap-3 text-xs text-amber-800">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">Store Verification In Progress</p>
            <p className="mt-0.5">
              Our single-city pilot team reviews business proofs within 2 hours. Once approved, you can immediately publish deals.
            </p>
          </div>
        </div>
      )}

      {/* Metrics Row (Real Data) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-400">Total Video Views</span>
            <TrendingUp className="h-4 w-4 text-primary" />
          </div>
          <span className="text-2xl font-black text-stone-900 font-mono mt-1 block">{totalViews}</span>
          <span className="text-[11px] text-stone-500">Across {reels.length} store videos</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-400">Active Deals</span>
            <Tag className="h-4 w-4 text-amber-600" />
          </div>
          <span className="text-2xl font-black text-stone-900 font-mono mt-1 block">{activeOffers}</span>
          <span className="text-[11px] text-stone-500">Live in shopper proximity feed</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-400">Counter Redemptions</span>
            <Users className="h-4 w-4 text-emerald-600" />
          </div>
          <span className="text-2xl font-black text-stone-900 font-mono mt-1 block">
            {analytics?.redemption_count ?? 0}
          </span>
          <span className="text-[11px] text-emerald-700 font-semibold">Verified by cashier scan</span>
        </div>
      </div>

      {/* Fast Operational Shortcuts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs flex items-center justify-between">
          <div className="space-y-1">
            <h4 className="font-extrabold text-xs text-stone-900 uppercase">Cashier Scanner PIN</h4>
            <p className="text-xs text-stone-500">Manage cashier credentials for in-store checkout verification.</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => onNavigateTab('staff')} className="text-xs shrink-0 ml-3 font-bold">
            Manage Staff
          </Button>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs flex items-center justify-between">
          <div className="space-y-1">
            <h4 className="font-extrabold text-xs text-stone-900 uppercase">Storefront Profile</h4>
            <p className="text-xs text-stone-500">View registered address, geofence, and business hours.</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => onNavigateTab('profile')} className="text-xs shrink-0 ml-3 font-bold">
            Store Profile
          </Button>
        </div>
      </div>
    </div>
  )
}
