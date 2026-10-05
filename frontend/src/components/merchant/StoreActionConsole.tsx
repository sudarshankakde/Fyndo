import React from 'react'
import { Store, KeyRound, Film, ArrowRight, ShieldCheck, Tag } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useTranslation } from '@/hooks/useTranslation'

interface StoreActionConsoleProps {
  isAuthenticated: boolean
  onOpenOnboard: () => void
  onOpenStaff: () => void
  onOpenUpload: () => void
  onRequireAuth: () => void
}

export const StoreActionConsole: React.FC<StoreActionConsoleProps> = ({
  isAuthenticated,
  onOpenOnboard,
  onOpenStaff,
  onOpenUpload,
  onRequireAuth,
}) => {
  const { t } = useTranslation()

  const handleAction = (action: () => void) => {
    if (!isAuthenticated) {
      onRequireAuth()
    } else {
      action()
    }
  }

  return (
    <div className="space-y-6">
      {/* Primary Action Panel: Publish Reel & In-Store Deal */}
      <div className="surface-card rounded-xl p-5 border border-stone-800 bg-stone-900/90 relative overflow-hidden">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="h-6 w-6 rounded bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-mono text-xs">
                01
              </span>
              <h2 className="text-base font-bold text-stone-100 font-display tracking-tight">
                Publish Short Reel & In-Store Coupon
              </h2>
            </div>
            <span className="font-mono text-[10px] uppercase text-stone-400 border border-stone-800 px-2 py-0.5 rounded">
              9:16 Vertical
            </span>
          </div>

          <p className="text-xs text-stone-400 leading-relaxed">
            Record raw in-store video (15–60s) or voiceovers. Attach a time-restricted discount voucher with automatic sector expiration.
          </p>

          {/* Sector Expiry Policy Badges */}
          <div className="flex flex-wrap gap-2 text-[10px] font-mono">
            <span className="px-2 py-1 rounded bg-stone-950 border border-stone-800 text-stone-300">
              Food Offers: 2–5 Days
            </span>
            <span className="px-2 py-1 rounded bg-stone-950 border border-stone-800 text-stone-300">
              Clothes & Shoes: Max 15 Days
            </span>
            <span className="px-2 py-1 rounded bg-stone-950 border border-stone-800 text-stone-300">
              Showrooms: Up to 60 Days
            </span>
          </div>

          <Button
            variant="primary"
            size="md"
            className="w-full justify-between group"
            onClick={() => handleAction(onOpenUpload)}
          >
            <div className="flex items-center gap-2">
              <Film className="h-4 w-4" />
              <span>Post Store Video & Offer</span>
            </div>
            <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
          </Button>
        </div>
      </div>

      {/* Secondary Dual Column Actions: Store Onboarding & Counter PIN */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Register Store Profile */}
        <div className="surface-card rounded-xl p-4 border border-stone-800 bg-stone-900/60 flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Store className="h-4 w-4 text-stone-400" />
              <h3 className="font-bold text-xs uppercase font-mono text-stone-200 tracking-wider">
                Store Profile
              </h3>
            </div>
            <p className="text-[11px] text-stone-400 leading-normal">
              Register your business name, street address, and store photo to get verified.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs"
            onClick={() => handleAction(onOpenOnboard)}
          >
            Register Your Store
          </Button>
        </div>

        {/* Cashier Scanner Staff PIN */}
        <div className="surface-card rounded-xl p-4 border border-stone-800 bg-stone-900/60 flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-stone-400" />
              <h3 className="font-bold text-xs uppercase font-mono text-stone-200 tracking-wider">
                Cashier Scanner PIN
              </h3>
            </div>
            <p className="text-[11px] text-stone-400 leading-normal">
              Create a 6-digit PIN for your counter staff so they can scan coupons at checkout.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs"
            onClick={() => handleAction(onOpenStaff)}
          >
            Create Counter PIN
          </Button>
        </div>
      </div>

      {/* Merchant Commitment Notice */}
      <div className="p-4 rounded-xl border border-stone-800 bg-stone-950/70 space-y-2 text-xs">
        <div className="flex items-center gap-2 font-mono text-[11px] font-bold text-amber-400">
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>OUR PROMISE TO LOCAL STORES</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-stone-400 font-mono">
          <div className="border-l border-stone-800 pl-2.5">
            <strong className="text-stone-300 block">100% Free Platform</strong>
            Keep all your revenue. Zero commission on customer sales.
          </div>
          <div className="border-l border-stone-800 pl-2.5">
            <strong className="text-stone-300 block">Fast Quality Check</strong>
            Videos are verified within 2 hours before appearing to shoppers.
          </div>
        </div>
      </div>
    </div>
  )
}
