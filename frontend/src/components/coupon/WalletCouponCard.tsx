import React from 'react'
import { QrCode, Clock, MapPin, CheckCircle2, AlertTriangle } from 'lucide-react'
import { UserWalletCoupon } from '@/types/coupon'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useAppDispatch } from '@/store'
import { openQrModal } from '@/store/slices/uiSlice'

interface WalletCouponCardProps {
  coupon: UserWalletCoupon
}

export const WalletCouponCard: React.FC<WalletCouponCardProps> = ({ coupon }) => {
  const dispatch = useAppDispatch()

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
    <div className="relative overflow-hidden rounded-3xl border border-stone-200 bg-white p-5 shadow-card hover:shadow-md transition-all font-sans">
      {/* Decorative scallop perforated punch holes */}
      <div className="absolute -left-3 top-1/2 -translate-y-1/2 h-6 w-6 rounded-full bg-[#FAFAFA] border border-stone-200" />
      <div className="absolute -right-3 top-1/2 -translate-y-1/2 h-6 w-6 rounded-full bg-[#FAFAFA] border border-stone-200" />

      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="space-y-1">
          <Badge
            variant={isRedeemed ? 'success' : isExpired ? 'destructive' : 'coral'}
          >
            {discountBadge}
          </Badge>
          <h3 className="font-extrabold text-base text-stone-900 tracking-tight leading-snug">
            {coupon.title}
          </h3>
          <p className="text-xs font-bold text-primary">{coupon.merchant_name}</p>
        </div>

        <div>
          {isRedeemed ? (
            <Badge variant="success">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Redeemed
            </Badge>
          ) : isExpired ? (
            <Badge variant="destructive">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Expired
            </Badge>
          ) : (
            <Badge variant="outline">
              <Clock className="h-3 w-3 mr-1 text-amber-500" />
              Valid till {formattedExpiry}
            </Badge>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-stone-500 mb-4 truncate">
        <MapPin className="h-3.5 w-3.5 text-stone-400 shrink-0" />
        <span className="truncate">{coupon.merchant_address || 'In-store deal'}</span>
      </div>

      {/* Action Button */}
      {!isRedeemed && !isExpired && (
        <Button
          variant="primary"
          size="md"
          className="w-full flex items-center justify-center gap-2 text-xs font-bold"
          onClick={() => dispatch(openQrModal(coupon.id))}
        >
          <QrCode className="h-4 w-4" />
          <span>Show at Counter</span>
        </Button>
      )}
    </div>
  )
}
