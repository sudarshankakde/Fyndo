import React, { useState } from 'react'
import { Film, PlusCircle, Clock, Eye, Tag, CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

interface OfferItem {
  id: string
  title: string
  sector: 'FOOD' | 'CLOTHES_FASHION' | 'ELECTRONICS'
  discountText: string
  minBill: string
  status: 'LIVE' | 'IN_REVIEW' | 'EXPIRED'
  expiresIn: string
  views: number
  claims: number
}

const INITIAL_OFFERS: OfferItem[] = [
  {
    id: 'OFR-101',
    title: 'Hot Crispy Jalebis & Fafda Morning Special',
    sector: 'FOOD',
    discountText: 'Flat 40% OFF',
    minBill: '₹200',
    status: 'LIVE',
    expiresIn: '2 days left (Food Limit)',
    views: 1840,
    claims: 142,
  },
  {
    id: 'OFR-102',
    title: 'Kaju Katli & Assorted Sweets Box',
    sector: 'FOOD',
    discountText: 'Flat ₹150 OFF',
    minBill: '₹500',
    status: 'LIVE',
    expiresIn: '3 days left',
    views: 920,
    claims: 78,
  },
  {
    id: 'OFR-103',
    title: 'Weekend Family Thali Feast Voucher',
    sector: 'FOOD',
    discountText: 'Buy 2 Get 1 Free',
    minBill: '₹600',
    status: 'IN_REVIEW',
    expiresIn: 'Review in progress (~2 hrs)',
    views: 0,
    claims: 0,
  },
]

interface MerchantOffersViewProps {
  onPostNew: () => void
}

export const MerchantOffersView: React.FC<MerchantOffersViewProps> = ({ onPostNew }) => {
  const [offers] = useState<OfferItem[]>(INITIAL_OFFERS)

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-stone-800">
        <div>
          <h2 className="text-xl font-bold text-stone-100 font-display">
            Store Offers & Video Reels
          </h2>
          <p className="text-xs text-stone-400 font-mono mt-0.5">
            15–60s vertical reels linked to sector-governed in-store discounts.
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={onPostNew} className="text-xs">
          <PlusCircle className="h-3.5 w-3.5 mr-1.5" />
          <span>Post New Offer</span>
        </Button>
      </div>

      {/* Offer Cards Grid */}
      <div className="space-y-3.5">
        {offers.map((offer) => {
          const isLive = offer.status === 'LIVE'
          const isInReview = offer.status === 'IN_REVIEW'

          return (
            <div
              key={offer.id}
              className="surface-card rounded-xl p-4 border border-stone-800 bg-stone-900/70 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs font-bold text-stone-400">
                    {offer.id}
                  </span>
                  <Badge variant={isLive ? 'success' : isInReview ? 'amber' : 'default'}>
                    {isLive ? 'Live in Stores' : isInReview ? 'Under Review (~2 hrs)' : 'Expired'}
                  </Badge>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-stone-950 border border-stone-800 text-stone-300">
                    {offer.sector}
                  </span>
                </div>

                <h3 className="font-bold text-sm text-stone-100 font-display">
                  {offer.title}
                </h3>

                <div className="flex items-center gap-4 text-xs font-mono text-stone-400 flex-wrap">
                  <span className="text-amber-400 font-semibold">{offer.discountText}</span>
                  <span>Min Bill: {offer.minBill}</span>
                  <span className="flex items-center gap-1 text-stone-400">
                    <Clock className="h-3 w-3" />
                    {offer.expiresIn}
                  </span>
                </div>
              </div>

              {/* Stats & Actions */}
              <div className="flex items-center gap-4 sm:border-l sm:border-stone-800/80 sm:pl-4 shrink-0 font-mono text-xs">
                <div className="text-center sm:text-right">
                  <span className="text-stone-500 text-[10px] block uppercase">Views</span>
                  <span className="text-sm font-bold text-stone-200">{offer.views}</span>
                </div>

                <div className="text-center sm:text-right">
                  <span className="text-stone-500 text-[10px] block uppercase">Claims</span>
                  <span className="text-sm font-bold text-amber-400">{offer.claims}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
