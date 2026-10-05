import { apiClient } from './apiClient'
import { ResponseEnvelope } from '@/types/api'
import { RedemptionVerifyResult } from '@/types/coupon'

interface VerifyRedemptionRequest {
  qr_payload: string
  cashier_lat?: number
  cashier_lon?: number
}

export const redemptionService = {
  async verifyAndRedeem(data: VerifyRedemptionRequest): Promise<RedemptionVerifyResult> {
    const res = await apiClient.post<ResponseEnvelope<RedemptionVerifyResult>>(
      '/redemptions/verify',
      data
    )
    return res.data.data
  },
}
