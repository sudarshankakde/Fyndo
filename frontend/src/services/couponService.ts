import { apiClient } from './apiClient'
import { ResponseEnvelope } from '@/types/api'
import { DynamicQrPayload, UserWalletCoupon } from '@/types/coupon'

interface ClaimCouponResponse {
  user_coupon_id: string
  status: string
  claimed_at: string
  expires_at: string
}

export const couponService = {
  async claimCoupon(templateId: string): Promise<ClaimCouponResponse> {
    const res = await apiClient.post<ResponseEnvelope<ClaimCouponResponse>>(
      `/coupons/${templateId}/claim`
    )
    return res.data.data
  },

  async getUserWallet(): Promise<UserWalletCoupon[]> {
    const res = await apiClient.get<ResponseEnvelope<UserWalletCoupon[]>>('/coupons/wallet')
    return res.data.data
  },

  async getDynamicQr(userCouponId: string): Promise<DynamicQrPayload> {
    const res = await apiClient.get<ResponseEnvelope<DynamicQrPayload>>(
      `/coupons/${userCouponId}/dynamic-qr`
    )
    return res.data.data
  },
}
