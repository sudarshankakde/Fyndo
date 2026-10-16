import React from 'react'
import { Button } from '@/components/ui/Button'

interface OfferCouponStepProps {
  title: string
  setTitle: (t: string) => void
  discountType: 'PERCENTAGE' | 'FLAT_AMOUNT' | 'BOGO'
  setDiscountType: (t: 'PERCENTAGE' | 'FLAT_AMOUNT' | 'BOGO') => void
  discountValue: number
  setDiscountValue: (v: number) => void
  minOrder: number
  setMinOrder: (v: number) => void
  validityDays: number
  setValidityDays: (v: number) => void
  sectorCeiling: number
  terms: string
  setTerms: (t: string) => void
  isSubmitting: boolean
  onBack: () => void
  onSubmit: () => void
}

export const OfferCouponStep: React.FC<OfferCouponStepProps> = ({
  title,
  setTitle,
  discountType,
  setDiscountType,
  discountValue,
  setDiscountValue,
  minOrder,
  setMinOrder,
  validityDays,
  setValidityDays,
  sectorCeiling,
  terms,
  setTerms,
  isSubmitting,
  onBack,
  onSubmit,
}) => {
  return (
    <div className="space-y-4 font-sans">
      <div>
        <h2 className="text-base font-extrabold text-stone-900">2. Customer Discount Terms</h2>
        <p className="text-xs text-stone-500">Configure the savings customers receive when they visit your shop.</p>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-bold text-stone-700 block">Offer Title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Flat 20% OFF on all sweets"
          className="h-11 w-full rounded-xl border border-stone-200 bg-white px-3.5 text-sm font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-bold text-stone-700 block">Discount Type</label>
          <select
            value={discountType}
            onChange={(e) => setDiscountType(e.target.value as any)}
            className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
          >
            <option value="PERCENTAGE">Percentage (%)</option>
            <option value="FLAT_AMOUNT">Flat Cash (₹)</option>
            <option value="BOGO">Buy 1 Get 1</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-bold text-stone-700 block">
            {discountType === 'PERCENTAGE' ? 'Discount Value (%)' : 'Amount (₹)'}
          </label>
          <input
            type="number"
            min={1}
            max={discountType === 'PERCENTAGE' ? 90 : 10000}
            value={discountValue}
            onChange={(e) => setDiscountValue(Number(e.target.value))}
            className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-bold text-stone-700 block">Min. Bill (₹)</label>
          <input
            type="number"
            min={0}
            value={minOrder}
            onChange={(e) => setMinOrder(Number(e.target.value))}
            className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-bold text-stone-700 block">Validity (Days)</label>
          <input
            type="number"
            min={1}
            max={sectorCeiling}
            value={validityDays}
            onChange={(e) =>
              setValidityDays(Math.min(Math.max(Number(e.target.value), 1), sectorCeiling))
            }
            className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-xs font-bold text-stone-700 block">Offer Terms</label>
        <textarea
          rows={2}
          value={terms}
          onChange={(e) => setTerms(e.target.value)}
          className="w-full rounded-xl border border-stone-200 bg-white p-2.5 text-xs text-stone-800 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs resize-none"
        />
      </div>

      <div className="bg-stone-50 rounded-xl p-3 border border-stone-200 flex items-center justify-between text-xs">
        <span className="text-stone-600 font-medium">Policy Limit:</span>
        <span className="font-bold text-primary">
          {validityDays} of max {sectorCeiling} days
        </span>
      </div>

      <div className="flex gap-2 pt-2">
        <Button variant="outline" onClick={onBack} className="flex-1">
          Back
        </Button>
        <Button
          disabled={title.trim().length < 3}
          isLoading={isSubmitting}
          onClick={onSubmit}
          className="flex-1"
        >
          Publish Store Offer
        </Button>
      </div>
    </div>
  )
}
