import React, { useState } from 'react'
import { Tag, Check, Sparkles } from 'lucide-react'
import confetti from 'canvas-confetti'
import { CouponFeedSummary } from '@/types/reel'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useWallet } from '@/hooks/useWallet'
import { useAppDispatch, useAppSelector } from '@/store'
import { setAuthModalOpen } from '@/store/slices/uiSlice'
import { useTranslation } from '@/hooks/useTranslation'

interface CouponBannerProps {
  coupon: CouponFeedSummary
}

export const CouponBanner: React.FC<CouponBannerProps> = ({ coupon }) => {
  const { t } = useTranslation()
  const dispatch = useAppDispatch()
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated)
  const { claimCoupon, isClaiming } = useWallet()
  const [isClaimedLocally, setIsClaimedLocally] = useState(false)

  const handleClaim = async (e: React.MouseEvent) => {
    e.stopPropagation()

    if (!isAuthenticated) {
      dispatch(setAuthModalOpen(true))
      return
    }

    try {
      await claimCoupon(coupon.id)
      setIsClaimedLocally(true)

      // Fire celebratory confetti burst!
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.8 },
        colors: ['#F59E0B', '#10B981', '#8B5CF6'],
      })
    } catch {
      // If already claimed or error
      setIsClaimedLocally(true)
    }
  }

  const discountLabel =
    coupon.discount_type === 'PERCENTAGE'
      ? `${coupon.discount_value}% OFF`
      : `₹${coupon.discount_value} OFF`

  return (
    <div className="glass-panel rounded-2xl p-3 border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-slate-900/80 to-slate-900/90 shadow-xl shadow-amber-500/5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="amber" className="font-extrabold text-xs">
              <Tag className="h-3 w-3 mr-1" />
              {discountLabel}
            </Badge>
            <span className="text-[11px] text-slate-400 font-medium">
              {coupon.validity_days} {t.days}
            </span>
          </div>

          <h4 className="text-sm font-bold text-white truncate">{coupon.title}</h4>
          {coupon.min_order_amount > 0 && (
            <p className="text-[11px] text-slate-400">
              {t.min_order}: ₹{coupon.min_order_amount}
            </p>
          )}
        </div>

        <Button
          size="sm"
          variant={isClaimedLocally ? 'outline' : 'gold'}
          disabled={isClaimedLocally || isClaiming}
          onClick={handleClaim}
          className="shrink-0"
        >
          {isClaimedLocally ? (
            <span className="flex items-center gap-1 text-emerald-400 font-semibold">
              <Check className="h-3.5 w-3.5" />
              {t.claimed}
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <Sparkles className="h-3.5 w-3.5" />
              {t.claim_coupon}
            </span>
          )}
        </Button>
      </div>
    </div>
  )
}
