export type CouponStatus = 'CLAIMED' | 'REDEEMED' | 'EXPIRED'

export interface UserWalletCoupon {
  id: string
  coupon_template_id: string
  title: string
  discount_type: 'PERCENTAGE' | 'FLAT_AMOUNT' | 'BOGO'
  discount_value: number
  min_order_amount: number
  validity_days: number
  merchant_name: string
  merchant_address: string
  status: CouponStatus
  claimed_at: string
  expires_at: string
  is_expired: boolean
}

export interface DynamicQrPayload {
  qr_payload: string
  totp_token: string
  time_step_remaining_seconds: number
  backup_offline_pin: string
}

export interface RedemptionVerifyResult {
  redemption_id: string
  status: string
  discount_applied: number
  customer_name?: string | null
  coupon_title: string
  timestamp: string
}
