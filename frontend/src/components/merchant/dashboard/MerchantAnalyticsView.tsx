import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, Users, RefreshCw, Ticket, DollarSign, Calendar } from 'lucide-react'
import { redemptionService, MerchantAnalyticsSummary } from '@/services/redemptionService'
import { MerchantRedemptionLedger } from '@/components/merchant/MerchantRedemptionLedger'
import { formatRupees } from '@/utils/format'

type DateRangeFilter = 'TODAY' | 'WEEK' | 'MONTH'

export const MerchantAnalyticsView: React.FC = () => {
  const [range, setRange] = useState<DateRangeFilter>('WEEK')

  const getDateParams = () => {
    const now = new Date()
    const toDate = now.toISOString()
    let fromDate: string

    if (range === 'TODAY') {
      const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      fromDate = startOfDay.toISOString()
    } else if (range === 'WEEK') {
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      fromDate = weekAgo.toISOString()
    } else {
      const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      fromDate = monthAgo.toISOString()
    }

    return { from_date: fromDate, to_date: toDate }
  }

  const { data: analytics, isLoading } = useQuery<MerchantAnalyticsSummary>({
    queryKey: ['merchant-analytics', range],
    queryFn: () => redemptionService.getMerchantAnalytics(getDateParams()),
  })

  return (
    <div className="space-y-6 font-sans text-stone-900">
      {/* Header & Date Range Filter Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-stone-200">
        <div>
          <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">
            In-Store Walk-ins & Savings Analytics
          </h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Verified customer redemptions driven by your video deals.
          </p>
        </div>

        <div className="flex items-center gap-1.5 bg-stone-100 p-1 rounded-2xl border border-stone-200 text-xs font-bold self-start sm:self-auto">
          <Calendar className="w-3.5 h-3.5 text-stone-400 ml-2" />
          <button
            onClick={() => setRange('TODAY')}
            className={`px-3 py-1 rounded-xl transition-all ${
              range === 'TODAY' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500 hover:text-stone-900'
            }`}
          >
            Today
          </button>
          <button
            onClick={() => setRange('WEEK')}
            className={`px-3 py-1 rounded-xl transition-all ${
              range === 'WEEK' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500 hover:text-stone-900'
            }`}
          >
            Last 7 Days
          </button>
          <button
            onClick={() => setRange('MONTH')}
            className={`px-3 py-1 rounded-xl transition-all ${
              range === 'MONTH' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500 hover:text-stone-900'
            }`}
          >
            Last 30 Days
          </button>
        </div>
      </div>

      {/* KPI Cards Strip */}
      {isLoading ? (
        <div className="py-12 text-center space-y-2">
          <RefreshCw className="w-6 h-6 text-primary animate-spin mx-auto" />
          <p className="text-xs text-stone-500 font-medium">Aggregating store ledger stats...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-400">
                Verified Redemptions
              </span>
              <Ticket className="w-4 h-4 text-primary" />
            </div>
            <p className="text-3xl font-black text-stone-900 font-mono">
              {analytics?.redemption_count ?? 0}
            </p>
            <p className="text-[11px] text-stone-500">Walk-in customers with in-app scan</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-400">
                Total Bill Value
              </span>
              <DollarSign className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-3xl font-black text-stone-900 font-mono">
              {formatRupees(analytics?.total_bill_amount ?? 0)}
            </p>
            <p className="text-[11px] text-stone-500">Gross counter checkout total</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-400">
                Customer Savings Given
              </span>
              <TrendingUp className="w-4 h-4 text-amber-600" />
            </div>
            <p className="text-3xl font-black text-stone-900 font-mono">
              {formatRupees(analytics?.total_discount_applied ?? 0)}
            </p>
            <p className="text-[11px] text-stone-500">Total in-store promotional discounts</p>
          </div>
        </div>
      )}

      {/* Honest Empty State if Zero Redemptions */}
      {analytics && analytics.redemption_count === 0 && (
        <div className="bg-white rounded-3xl border border-stone-200/80 p-8 text-center space-y-2 max-w-md mx-auto">
          <Ticket className="w-8 h-8 text-stone-400 mx-auto" />
          <h4 className="text-sm font-black text-stone-900">No redemptions for this period</h4>
          <p className="text-xs text-stone-500 leading-relaxed">
            When nearby customers present dynamic QR codes at your checkout counter, redemptions will appear here in real time.
          </p>
        </div>
      )}

      {/* Embedded Live Redemption Ledger */}
      <div className="pt-2">
        <MerchantRedemptionLedger />
      </div>
    </div>
  )
}
