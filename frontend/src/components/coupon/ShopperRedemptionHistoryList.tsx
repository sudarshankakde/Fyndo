import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, RefreshCw, Receipt } from 'lucide-react'
import { redemptionService, ShopperRedemptionRecord } from '@/services/redemptionService'
import { formatRupees } from '@/utils/format'

export const ShopperRedemptionHistoryList: React.FC = () => {
  const { data: history = [], isLoading } = useQuery<ShopperRedemptionRecord[]>({
    queryKey: ['shopper-redemption-history'],
    queryFn: () => redemptionService.getShopperHistory(),
  })

  if (isLoading) {
    return (
      <div className="py-12 text-center space-y-2">
        <RefreshCw className="w-6 h-6 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Loading redemption receipts...</p>
      </div>
    )
  }

  if (history.length === 0) {
    return (
      <div className="bg-white rounded-3xl border border-stone-200/80 p-8 text-center space-y-2 max-w-md mx-auto">
        <Receipt className="w-8 h-8 text-stone-400 mx-auto" />
        <h4 className="text-sm font-black text-stone-800">No In-Store Redemptions Yet</h4>
        <p className="text-xs text-stone-500">
          When you redeem savings at partner counters, your transaction receipts and total rupee savings will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3 font-sans">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500">
          Settled Counter Receipts ({history.length})
        </h3>
        <span className="text-xs font-bold text-emerald-700">Verified In-Store Savings</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {history.map((item) => (
          <div
            key={item.redemption_id}
            className="bg-white rounded-2xl border border-stone-200/80 p-4 shadow-2xs space-y-3"
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-sm font-black text-stone-900">{item.merchant_name}</h4>
                <p className="text-[11px] text-stone-500">{item.coupon_title}</p>
              </div>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3 h-3" />
                Settled
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 bg-stone-50 p-2.5 rounded-xl text-center text-xs">
              <div>
                <p className="text-[10px] text-stone-400 uppercase font-bold">Total Bill</p>
                <p className="font-bold text-stone-800 font-mono">{formatRupees(item.bill_amount)}</p>
              </div>
              <div>
                <p className="text-[10px] text-emerald-600 uppercase font-bold">You Saved</p>
                <p className="font-extrabold text-emerald-700 font-mono">
                  -{formatRupees(item.discount_applied)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-stone-400 uppercase font-bold">Paid at Counter</p>
                <p className="font-black text-stone-900 font-mono">
                  {formatRupees(Math.max(0, item.bill_amount - item.discount_applied))}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between text-[10px] text-stone-400 font-mono pt-1 border-t border-stone-100">
              <span>Receipt: {item.redemption_id.slice(0, 8).toUpperCase()}</span>
              <span>{new Date(item.created_at).toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
