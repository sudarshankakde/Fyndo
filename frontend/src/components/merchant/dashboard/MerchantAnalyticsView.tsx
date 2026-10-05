import React from 'react'
import { TrendingUp, Users, Clock, ShieldCheck, ArrowUpRight, DollarSign } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'

export const MerchantAnalyticsView: React.FC = () => {
  const days = [
    { day: 'Mon', walkins: 28, pct: '45%' },
    { day: 'Tue', walkins: 34, pct: '55%' },
    { day: 'Wed', walkins: 38, pct: '60%' },
    { day: 'Thu', walkins: 42, pct: '68%' },
    { day: 'Fri', walkins: 56, pct: '88%' },
    { day: 'Sat', walkins: 64, pct: '100%' },
    { day: 'Sun', walkins: 61, pct: '95%' },
  ]

  return (
    <div className="space-y-6">
      <div className="pb-2 border-b border-stone-800">
        <h2 className="text-xl font-bold text-stone-100 font-display">
          In-Store Footfall & Walk-in Analytics
        </h2>
        <p className="text-xs text-stone-400 font-mono mt-0.5">
          Verified customer visits driven directly by 15–60s video discovery.
        </p>
      </div>

      {/* Primary KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/60">
          <span className="font-mono text-[10px] text-stone-400 uppercase block">Weekly Walk-ins</span>
          <span className="text-3xl font-bold font-mono text-stone-100 mt-1 block">323</span>
          <span className="font-mono text-[10px] text-emerald-400 font-medium">+24% vs last week</span>
        </div>

        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/60">
          <span className="font-mono text-[10px] text-stone-400 uppercase block">Discounts Given</span>
          <span className="text-3xl font-bold font-mono text-amber-400 mt-1 block">₹28,450</span>
          <span className="font-mono text-[10px] text-stone-400">Total in-store savings</span>
        </div>

        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/60">
          <span className="font-mono text-[10px] text-stone-400 uppercase block">Pilot Commission Fee</span>
          <span className="text-3xl font-bold font-mono text-emerald-400 mt-1 block">₹0.00</span>
          <span className="font-mono text-[10px] text-emerald-400 font-medium">100% Free for Stores</span>
        </div>
      </div>

      {/* Weekly Footfall Activity Bar Visual */}
      <div className="surface-card p-5 rounded-xl border border-stone-800 bg-stone-900/80 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-stone-100 font-display">
            Daily Verified In-Store Walk-ins
          </h3>
          <span className="font-mono text-xs text-stone-400">Past 7 Days</span>
        </div>

        <div className="grid grid-cols-7 gap-2 items-end h-40 pt-4 pb-2 border-b border-stone-800">
          {days.map((item) => (
            <div key={item.day} className="flex flex-col items-center gap-1.5 h-full justify-end">
              <span className="font-mono text-[10px] text-stone-400 font-semibold">{item.walkins}</span>
              <div
                style={{ height: item.pct }}
                className="w-full max-w-[28px] rounded bg-amber-500/80 hover:bg-amber-400 transition-colors"
              />
              <span className="font-mono text-[10px] text-stone-400 mt-1">{item.day}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between text-xs font-mono text-stone-400">
          <span>Peak Traffic: Friday & Saturday</span>
          <span className="text-amber-400">Avg. 46 walk-ins / day</span>
        </div>
      </div>

      {/* Peak Hours & Neighborhood Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/40 space-y-2">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-amber-400" />
            <h4 className="font-bold text-xs uppercase font-mono text-stone-200">
              Peak Walk-in Hours
            </h4>
          </div>
          <p className="text-xs text-stone-300">
            <strong>5:30 PM – 8:45 PM</strong> accounts for 58% of all in-store coupon redemptions.
          </p>
          <p className="text-[11px] text-stone-400">
            Consider posting fresh evening menu or retail reels around 4:00 PM for maximum footfall.
          </p>
        </div>

        <div className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/40 space-y-2">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-emerald-400" />
            <h4 className="font-bold text-xs uppercase font-mono text-stone-200">
              Nearby Customer Distance
            </h4>
          </div>
          <p className="text-xs text-stone-300">
            <strong>68% of shoppers</strong> redeemed coupons within 2km of your Sitabuldi shop.
          </p>
          <p className="text-[11px] text-stone-400">
            28% from 5km radius (Dharampeth, Ramdaspeth, Sadar).
          </p>
        </div>
      </div>
    </div>
  )
}
