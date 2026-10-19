import React from 'react'
import { ShieldCheck } from 'lucide-react'

export const LoginHeroSection: React.FC = () => {
  return (
    <div className="lg:col-span-7 space-y-6">
      <div className="space-y-3">
        <span className="font-mono text-[11px] text-amber-400 uppercase tracking-widest px-2 py-0.5 rounded border border-amber-800/60 bg-amber-950/20">
          RETAIL FOOTFALL ENGINE
        </span>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-stone-100 font-display tracking-tight leading-[1.1]">
          Short Video Discovery for Local Physical Stores.
        </h1>
        <p className="text-sm sm:text-base text-stone-400 leading-relaxed max-w-xl font-sans">
          Connect with nearby shoppers through 15–60s vertical reels. Customers claim digital discount vouchers on their mobile app and redeem them exclusively at your physical counter using rotating security codes.
        </p>
      </div>

      {/* Operational Guarantees */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs pt-2">
        <div className="surface-card p-3.5 rounded-lg border border-stone-800 bg-stone-900/60 space-y-1">
          <strong className="text-stone-200 block">100% Free for Stores</strong>
          <p className="text-stone-400 text-[11px]">
            Zero commissions and zero listing fees on customer sales.
          </p>
        </div>
        <div className="surface-card p-3.5 rounded-lg border border-stone-800 bg-stone-900/60 space-y-1">
          <strong className="text-stone-200 block">In-Person Verification</strong>
          <p className="text-stone-400 text-[11px]">
            Codes only validate when customer is physically at the billing counter.
          </p>
        </div>
      </div>
    </div>
  )
}
