import { http } from './http'
import { DynamicQrPayload, UserWalletCoupon } from '@/types/coupon'

export interface ClaimCouponResponse {
  user_coupon_id: string
  status: string
  claimed_at: string
  expires_at: string
}

export const couponService = {
  async claimCoupon(templateId: string): Promise<ClaimCouponResponse> {
    return http.post<any, ClaimCouponResponse>(`/coupons/${templateId}/claim`)
  },

  async getUserWallet(): Promise<UserWalletCoupon[]> {
    return http.get<any, UserWalletCoupon[]>('/coupons/wallet')
  },

  async getDynamicQr(userCouponId: string): Promise<DynamicQrPayload> {
    return http.get<any, DynamicQrPayload>(`/coupons/${userCouponId}/dynamic-qr`)
  },
}
