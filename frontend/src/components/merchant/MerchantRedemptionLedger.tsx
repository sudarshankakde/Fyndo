import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Receipt, RefreshCw, CheckCircle2 } from 'lucide-react'
import { redemptionService, MerchantRedemptionRecord } from '@/services/redemptionService'
import { formatRupees } from '@/utils/format'
import { Button } from '@/components/ui/Button'

export const MerchantRedemptionLedger: React.FC = () => {
  const today = new Date().toISOString().split('T')[0]

  const {
    data: records = [],
    isLoading,
    refetch,
    isRefetching,
  } = useQuery<MerchantRedemptionRecord[]>({
    queryKey: ['merchant', 'redemptions', today],
    queryFn: () => redemptionService.getMerchantRedemptions({ from_date: `${today}T00:00:00Z` }),
    refetchInterval: 15000,
  })

  return (
    <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-card space-y-4 font-sans text-stone-900">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-black text-stone-900 tracking-tight">Today's In-Store Redemptions</h3>
          <p className="text-xs text-stone-500">Live verified customer checkouts at your counter</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading || isRefetching}
          className="text-xs gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-xs text-stone-400 font-semibold">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary" />
          Loading transactions...
        </div>
      ) : records.length === 0 ? (
        <div className="py-8 text-center text-stone-400 space-y-2 bg-stone-50/60 rounded-2xl border border-stone-100">
          <Receipt className="w-7 h-7 mx-auto text-stone-300" />
          <p className="text-xs font-semibold text-stone-600">No customer redemptions recorded today.</p>
          <p className="text-[11px] text-stone-400">Transactions appear here as cashier scans customer codes.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-stone-200 text-stone-400 uppercase text-[10px] tracking-wider">
                <th className="pb-2.5 font-bold">Time</th>
                <th className="pb-2.5 font-bold">Customer</th>
                <th className="pb-2.5 font-bold">Coupon Offer</th>
                <th className="pb-2.5 font-bold text-right">Bill (₹)</th>
                <th className="pb-2.5 font-bold text-right">Discount</th>
                <th className="pb-2.5 font-bold text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 font-medium">
              {records.map((r) => {
                const time = new Date(r.created_at).toLocaleTimeString('en-IN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })
                return (
                  <tr key={r.redemption_id} className="hover:bg-stone-50/50">
                    <td className="py-3 text-stone-500 font-mono text-[11px]">{time}</td>
                    <td className="py-3 font-bold text-stone-900">{r.shopper_name}</td>
                    <td className="py-3 text-stone-600 truncate max-w-[150px]">{r.coupon_title}</td>
                    <td className="py-3 text-right font-mono font-bold text-stone-900">{formatRupees(r.bill_amount)}</td>
                    <td className="py-3 text-right font-mono font-bold text-emerald-600">
                      -{formatRupees(r.discount_applied)}
                    </td>
                    <td className="py-3 text-center">
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        Settled
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
