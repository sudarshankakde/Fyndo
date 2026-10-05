import React from 'react'
import { PlusCircle, KeyRound, Store, ArrowUpRight, TrendingUp, Users, Tag } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { OperationsLedgerAnchor } from '@/components/merchant/OperationsLedgerAnchor'
import { MerchantTab } from '@/components/merchant/dashboard/MerchantSidebar'

interface MerchantOverviewViewProps {
  onNavigateTab: (tab: MerchantTab) => void
}

export const MerchantOverviewView: React.FC<MerchantOverviewViewProps> = ({ onNavigateTab }) => {
  return (
    <div className="space-y-6">
      {/* Top Welcome Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-stone-800">
        <div>
          <h2 className="text-xl font-bold text-stone-100 font-display">
            Counter Overview & Live Telemetry
          </h2>
          <p className="text-xs text-stone-400 font-mono mt-0.5">
            Real-time in-store customer walk-ins and billing counter verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => onNavigateTab('new-offer')}
            className="text-xs"
          >
            <PlusCircle className="h-3.5 w-3.5 mr-1.5" />
            <span>Post New Offer</span>
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/60">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase text-stone-400">Total Video Views</span>
            <TrendingUp className="h-3.5 w-3.5 text-amber-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-stone-100 mt-1 block">4,310</span>
          <span className="font-mono text-[10px] text-emerald-400">+18% nearby shoppers this week</span>
        </div>

        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/60">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase text-stone-400">Coupons in Wallets</span>
            <Tag className="h-3.5 w-3.5 text-stone-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-amber-400 mt-1 block">284</span>
          <span className="font-mono text-[10px] text-stone-400">Active saved vouchers</span>
        </div>

        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/60">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase text-stone-400">Redeemed In-Store</span>
            <Users className="h-3.5 w-3.5 text-emerald-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-emerald-400 mt-1 block">142</span>
          <span className="font-mono text-[10px] text-emerald-400">Verified at cashier counter</span>
        </div>
      </div>

      {/* Live Operations Ledger Visual Anchor */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-mono text-stone-400 px-1">
          <span>ACTIVE COUNTER TERMINAL</span>
          <span className="text-emerald-400">LIVE SYNC READY</span>
        </div>
        <OperationsLedgerAnchor />
      </div>

      {/* Fast Operational Shortcuts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/40 flex items-center justify-between">
          <div className="space-y-1">
            <h4 className="font-bold text-xs text-stone-200 font-mono uppercase">
              Configure Cashier PIN
            </h4>
            <p className="text-[11px] text-stone-400">
              Add or rotate 6-digit PINs for your store staff counter scanner.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onNavigateTab('staff')}
            className="text-xs shrink-0 ml-3"
          >
            Manage Staff
          </Button>
        </div>

        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/40 flex items-center justify-between">
          <div className="space-y-1">
            <h4 className="font-bold text-xs text-stone-200 font-mono uppercase">
              Update Store Details
            </h4>
            <p className="text-[11px] text-stone-400">
              Verify your physical address, category, and opening hours.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onNavigateTab('profile')}
            className="text-xs shrink-0 ml-3"
          >
            Edit Profile
          </Button>
        </div>
      </div>
    </div>
  )
}
