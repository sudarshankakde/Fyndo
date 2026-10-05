import React from 'react'
import { QrCode, Clock, MapPin, CheckCircle2, AlertTriangle } from 'lucide-react'
import { UserWalletCoupon } from '@/types/coupon'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useAppDispatch } from '@/store'
import { openQrModal } from '@/store/slices/uiSlice'
import { useTranslation } from '@/hooks/useTranslation'

interface WalletCouponCardProps {
  coupon: UserWalletCoupon
}

export const WalletCouponCard: React.FC<WalletCouponCardProps> = ({ coupon }) => {
  const dispatch = useAppDispatch()
  const { t } = useTranslation()

  const isRedeemed = coupon.status === 'REDEEMED'
  const isExpired = coupon.status === 'EXPIRED' || coupon.is_expired

  const discountBadge =
    coupon.discount_type === 'PERCENTAGE'
      ? `${coupon.discount_value}% OFF`
      : `₹${coupon.discount_value} OFF`

  const formattedExpiry = new Date(coupon.expires_at).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
  })

  return (
    <div className="surface-card relative overflow-hidden rounded-xl border border-stone-800 bg-stone-900/90 p-4 transition-colors hover:border-stone-700">
      {/* Visual coupon perforated punch holes */}
      <div className="absolute -left-3 top-1/2 -translate-y-1/2 h-5 w-5 rounded-full bg-stone-950 border border-stone-800" />
      <div className="absolute -right-3 top-1/2 -translate-y-1/2 h-5 w-5 rounded-full bg-stone-950 border border-stone-800" />

      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <Badge
            variant={isRedeemed ? 'success' : isExpired ? 'destructive' : 'amber'}
            className="mb-1.5"
          >
            {discountBadge}
          </Badge>
          <h3 className="font-bold text-base text-stone-100 font-display">{coupon.title}</h3>
          <p className="text-xs text-amber-400 font-mono font-medium">{coupon.merchant_name}</p>
        </div>

        <div>
          {isRedeemed ? (
            <Badge variant="success" className="py-0.5">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Redeemed
            </Badge>
          ) : isExpired ? (
            <Badge variant="destructive" className="py-0.5">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Expired
            </Badge>
          ) : (
            <Badge variant="outline" className="py-0.5 text-stone-300">
              <Clock className="h-3 w-3 mr-1 text-amber-400" />
              Till {formattedExpiry}
            </Badge>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-stone-400 mb-4 truncate font-mono">
        <MapPin className="h-3.5 w-3.5 text-stone-500 shrink-0" />
        <span className="truncate">{coupon.merchant_address || 'In-store discount'}</span>
      </div>

      {/* Action Button */}
      {!isRedeemed && !isExpired && (
        <Button
          variant="primary"
          size="md"
          className="w-full flex items-center justify-center gap-2 font-mono text-xs font-semibold"
          onClick={() => dispatch(openQrModal(coupon.id))}
        >
          <QrCode className="h-4 w-4" />
          <span>Show Security Code at Counter</span>
        </Button>
      )}
    </div>
  )
}
