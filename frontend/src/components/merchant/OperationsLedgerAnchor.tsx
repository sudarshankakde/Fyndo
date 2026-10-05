import React, { useState, useEffect } from 'react'
import { ShieldCheck, Activity, Terminal, ArrowUpRight, Clock, MapPin, CheckCircle2 } from 'lucide-react'

interface RedemptionEvent {
  id: string
  time: string
  deal: string
  sector: 'FOOD' | 'CLOTHES' | 'ELECTRONICS'
  totpSample: string
  savings: string
}

const INITIAL_EVENTS: RedemptionEvent[] = [
  {
    id: 'TXN-9021',
    time: '2m ago',
    deal: 'Sitabuldi Haldirams • 40% OFF',
    sector: 'FOOD',
    totpSample: '849 201',
    savings: '₹140',
  },
  {
    id: 'TXN-9020',
    time: '8m ago',
    deal: 'Dharampeth Raymond • Flat ₹500 OFF',
    sector: 'CLOTHES',
    totpSample: '392 118',
    savings: '₹500',
  },
  {
    id: 'TXN-9019',
    time: '19m ago',
    deal: 'Sadhar Croma Store • 15% In-Store',
    sector: 'ELECTRONICS',
    totpSample: '771 904',
    savings: '₹620',
  },
]

export const OperationsLedgerAnchor: React.FC = () => {
  const [secondsRemaining, setSecondsRemaining] = useState(48)
  const [events] = useState<RedemptionEvent[]>(INITIAL_EVENTS)

  // Realistic dynamic TOTP ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsRemaining((prev) => (prev <= 1 ? 60 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="surface-card rounded-xl border border-stone-800 bg-stone-900/90 divide-y divide-stone-800 text-stone-200">
      {/* Visual Anchor Header / Counter Scanner Status */}
      <div className="p-4 flex items-center justify-between bg-stone-950/60">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-stone-200 uppercase tracking-wider">
                Store Counter Scanner
              </span>
              <span className="font-mono text-[9px] px-1.5 py-0.2 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/80">
                Online & Ready
              </span>
            </div>
            <p className="font-mono text-[10px] text-stone-400">
              Sitabuldi Main Counter • Active
            </p>
          </div>
        </div>

        <div className="text-right font-mono">
          <span className="text-[10px] text-stone-400 block uppercase">Security Code</span>
          <span className="text-xs font-bold text-amber-400">Refreshes in {secondsRemaining}s</span>
        </div>
      </div>

      {/* Structural Operational Metrics */}
      <div className="grid grid-cols-2 divide-x divide-stone-800 bg-stone-900/40">
        <div className="p-4">
          <span className="font-mono text-[10px] uppercase text-stone-400 block tracking-wider">
            Walk-in Customers Today
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-stone-100">42</span>
            <span className="text-[11px] font-mono text-emerald-400 font-medium">In-Store Visits</span>
          </div>
          <p className="text-[10px] text-stone-400 mt-1">Verified at billing counter</p>
        </div>

        <div className="p-4">
          <span className="font-mono text-[10px] uppercase text-stone-400 block tracking-wider">
            Customer Discounts Given
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-amber-400">₹6,840</span>
            <span className="text-[11px] font-mono text-stone-400 font-medium">Sitabuldi Store</span>
          </div>
          <p className="text-[10px] text-stone-400 mt-1">Commission: ₹0 (100% Free for Stores)</p>
        </div>
      </div>

      {/* Live In-Store Ledger Activity */}
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-mono text-[11px] font-semibold text-stone-300">
            <Terminal className="h-3.5 w-3.5 text-amber-400" />
            <span>RECENT COUNTER REDEMPTIONS</span>
          </div>
          <span className="font-mono text-[10px] text-stone-400">Updated Live</span>
        </div>

        <div className="space-y-2">
          {events.map((evt) => (
            <div
              key={evt.id}
              className="p-2.5 rounded border border-stone-800/80 bg-stone-950/50 flex items-center justify-between gap-3 text-xs"
            >
              <div className="space-y-0.5 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] font-semibold text-stone-400">
                    {evt.id}
                  </span>
                  <span className="font-mono text-[9px] px-1 rounded bg-stone-800 text-stone-300">
                    {evt.sector}
                  </span>
                  <span className="font-mono text-[10px] text-stone-400">{evt.time}</span>
                </div>
                <p className="font-medium text-stone-200 truncate text-[11px]">{evt.deal}</p>
              </div>

              <div className="text-right shrink-0">
                <span className="font-mono text-xs font-bold text-emerald-400 block">
                  {evt.savings}
                </span>
                <span className="font-mono text-[9px] text-stone-400">
                  Code: {evt.totpSample}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* In-Store Guarantee Callout */}
      <div className="p-3 bg-stone-950/80 flex items-center justify-between text-[11px] font-mono text-stone-400">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-3.5 w-3.5 text-amber-400 shrink-0" />
          <span>Verified in-person store redemption</span>
        </div>
        <span className="text-emerald-400">SHOP VERIFIED</span>
      </div>
    </div>
  )
}
